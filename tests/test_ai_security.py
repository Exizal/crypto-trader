import json
import hashlib
import time
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_review
from live_engine import Engine, StateStore
from secure_transport import NoRedirect, secure_json

TEMP = Path(__file__).resolve().parents[1] / "work" / "ai-tests"
TEMP.mkdir(parents=True, exist_ok=True)


def snapshot():
    return {
        "symbol": "BTCUSDT",
        "signal_timestamp": 123456789,
        "bid": 79999,
        "ask": 80000,
        "ema_fast": 79900,
        "ema_slow": 79800,
        "atr": 100,
        "entry": 80040,
        "stop": 79840,
        "target": 80440,
        "quantity": 0.00009,
        "planned_loss": 0.036,
    }


def response(verdict=None):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            verdict
                            or {
                                "decision": "approve",
                                "confidence": 90,
                                "reason": "Trend supported.",
                            }
                        ),
                    }
                ],
            }
        ],
    }


class AISecurityTests(unittest.TestCase):
    def config(self, root):
        ai_review.save_settings(
            root,
            {
                "key": "placeholder-openai-token-0000",
                "model": ai_review.DEFAULT_MODEL,
                "day": "",
                "calls": 0,
                "reviews": {},
            },
        )

    def test_no_ai_key_means_no_approval(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            self.assertFalse(ai_review.Gate(Path(folder)).review(snapshot())["approved"])

    def test_missing_model_approval_cannot_submit_an_order(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            api = Mock()
            engine = Engine(Path(folder), api, {"key": "dummy", "secret": "dummy"})
            engine.state = {"active": None, "halted": False, "last_signal": 0}
            engine.submit({"entry": "80040"}, 100)
            api.request.assert_not_called()

    def test_ai_approval_cannot_be_reused_for_a_modified_or_expired_plan(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            api = Mock()
            engine = Engine(Path(folder), api, {"key": "dummy", "secret": "dummy"})
            engine.state = {"active": None, "halted": False, "last_signal": 0}
            plan = {"entry": "80040"}
            digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
            engine._approval = (100, digest, time.monotonic())
            engine.submit({"entry": "90000"}, 100)
            api.request.assert_not_called()
            engine._approval = (100, digest, time.monotonic() - 61)
            engine.submit(plan, 100)
            api.request.assert_not_called()

    def test_snapshot_rejects_credentials_account_data_and_non_finite_values(self):
        for key, value in [("api_secret", "dummy"), ("account_uid", 123), ("portfolio", {})]:
            candidate = snapshot()
            candidate[key] = value
            with self.assertRaises(ValueError):
                ai_review.validate_snapshot(candidate)
        candidate = snapshot()
        candidate["ask"] = float("nan")
        with self.assertRaises(ValueError):
            ai_review.validate_snapshot(candidate)

    def test_ai_response_cannot_inject_order_fields_or_tools(self):
        for candidate in [
            response({"decision": "approve", "confidence": 100, "reason": "ok", "quantity": 100}),
            {"status": "completed", "output": [{"type": "function_call", "name": "withdraw"}]},
            {"status": "incomplete", "output": []},
            response({"decision": "approve", "confidence": True, "reason": "ok"}),
        ]:
            self.assertIsNone(ai_review.parse_response(candidate))

    def test_approval_uses_structured_output_and_sends_no_exchange_credentials(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            self.config(root)
            with patch("ai_review.secure_json", return_value=response()) as api:
                verdict = ai_review.Gate(root).review(snapshot())
                request = api.call_args.args[0]
                payload = json.loads(request.data)
                self.assertEqual(payload["text"]["format"]["type"], "json_schema")
                self.assertTrue(payload["text"]["format"]["strict"])
                self.assertFalse(payload["store"])
                self.assertNotIn("tools", payload)
                self.assertLessEqual(payload["max_output_tokens"], 512)
                self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
                self.assertNotIn("key", payload["input"][0]["content"])
                self.assertNotIn("placeholder-openai-token", request.data.decode())
                self.assertTrue(verdict["approved"])

    def test_ai_failure_does_not_retry_same_signal_with_a_changed_quote(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            self.config(root)
            with patch("ai_review.secure_json", side_effect=TimeoutError) as api:
                gate = ai_review.Gate(root)
                self.assertFalse(gate.review(snapshot())["approved"])
                self.assertFalse(gate.review(snapshot())["approved"])
                changed = snapshot()
                changed["ask"] = 80001
                self.assertFalse(gate.review(changed)["approved"])
                self.assertEqual(api.call_count, 1)

    def test_daily_ai_attempt_limit_survives_restart(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            self.config(root)
            with patch("ai_review.secure_json", return_value=response()) as api:
                for n in range(8):
                    candidate = snapshot()
                    candidate["signal_timestamp"] += n
                    ai_review.Gate(root).review(candidate)
                self.assertEqual(api.call_count, ai_review.MAX_CALLS_DAY)

    def test_secrets_are_encrypted_on_disk(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            root = Path(folder)
            self.config(root)
            raw = (root / ".private" / "ai.bin").read_bytes()
            self.assertNotIn(b"placeholder-openai-token", raw)
            self.assertEqual(ai_review.read_settings(root)["model"], ai_review.DEFAULT_MODEL)

    def test_redirect_handler_does_not_forward_credentials(self):
        request = urllib.request.Request(
            "https://api.binance.com/api/v3/account", headers={"X-MBX-APIKEY": "dummy"}
        )
        self.assertIsNone(
            NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://example.com")
        )

    def test_credential_hosts_http_and_userinfo_are_rejected(self):
        for url in [
            "http://api.openai.com/v1/responses",
            "https://api.openai.com.evil.test",
            "https://api.binance.com@evil.test",
            "https://api.openai.com:444/v1/responses",
        ]:
            with patch("urllib.request.build_opener") as opener:
                with self.assertRaises(ValueError):
                    secure_json(urllib.request.Request(url))
                opener.assert_not_called()

    def test_response_size_is_bounded(self):
        result = Mock()
        result.__enter__ = Mock(return_value=result)
        result.__exit__ = Mock(return_value=None)
        result.read.return_value = b"x" * 20
        opener = Mock()
        opener.open.return_value = result
        with patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                secure_json(
                    urllib.request.Request("https://api.openai.com/v1/models"), max_bytes=10
                )

    def test_stale_ledger_is_detected_from_untracked_app_order(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            api = Mock()
            api.request.return_value = [{"clientOrderId": "ct_untracked_buy"}]
            engine = Engine(Path(folder), api, {"key": "dummy", "secret": "dummy"})
            engine.state = {"cycles": [], "active": None}
            with self.assertRaises(ValueError):
                engine.verify_known_orders()

    def test_legacy_authenticated_ledger_is_read_and_upgraded(self):
        with TemporaryDirectory(dir=TEMP) as folder:
            store = StateStore(Path(folder), "dummy")
            state = {"cash": "10"}
            store.path.write_text(json.dumps({"state": state, "mac": store.tag(state, version=1)}))
            self.assertEqual(store.read(), state)
            store.write(state)
            self.assertEqual(json.loads(store.path.read_text())["version"], 2)


if __name__ == "__main__":
    unittest.main()
