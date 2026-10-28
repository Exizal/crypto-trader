from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sys
import unittest
import urllib.error
import hashlib
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live_api import Binance, ExchangeError, fee_bound
from live_engine import Engine, StateStore, plan_entry, number
import credential_store

TEST_TEMP = Path(__file__).resolve().parents[1] / "work" / "live-test-files"
TEST_TEMP.mkdir(parents=True, exist_ok=True)


def rules():
    return {
        "status": "TRADING",
        "ocoAllowed": True,
        "otoAllowed": True,
        "orderTypes": ["STOP_LOSS"],
        "filters": [
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.00001",
                "maxQty": "9000",
                "stepSize": "0.00001",
            },
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "NOTIONAL", "minNotional": "5", "maxNotional": "9000000"},
        ],
    }


class LiveTests(unittest.TestCase):
    def test_order_sizing_within_budget_risk_and_protected_minimum(self):
        plan = plan_entry(80000, 79999, 100, 10, 0, ".001", rules())
        self.assertIsNotNone(plan)
        self.assertLessEqual(number(plan["quantity"]) * number(plan["entry"]), number("7.5"))
        self.assertLessEqual(number(plan["planned_loss"]), number(".1"))
        self.assertGreaterEqual(number(plan["exit_quantity"]) * number(plan["stop"]), number("5.5"))

    def test_does_not_increase_risk_to_meet_minimum(self):
        self.assertIsNone(plan_entry(80000, 79999, 5000, 10, 0, ".001", rules()))
        self.assertIsNone(plan_entry(80000, 79999, 100, 4, 0, ".001", rules()))

    def test_existing_residual_counts_toward_position_limit(self):
        self.assertIsNone(plan_entry(80000, 79999, 100, 10, ".00009", ".001", rules()))

    def test_refuses_missing_native_protection_or_wide_spread(self):
        info = rules()
        info["otoAllowed"] = False
        self.assertIsNone(plan_entry(80000, 79999, 100, 10, 0, ".001", info))
        self.assertIsNone(plan_entry(80000, 78000, 100, 10, 0, ".001", rules()))

    def test_transport_cannot_access_withdrawal_transfer_or_market_order(self):
        api = Binance("dummy", "dummy", armed=True)
        with patch("urllib.request.urlopen") as network:
            for method, path in [
                ("POST", "/sapi/v1/capital/withdraw/apply"),
                ("POST", "/api/v3/order"),
                ("POST", "/sapi/v1/asset/transfer"),
                ("DELETE", "/api/v3/openOrders"),
            ]:
                with self.assertRaises(ValueError):
                    api.request(method, path, {})
            network.assert_not_called()

    def test_unarmed_transport_cannot_place_orders(self):
        with patch("urllib.request.urlopen") as network:
            with self.assertRaises(ValueError):
                Binance("dummy", "dummy").request("POST", "/api/v3/orderList/otoco", {})
            network.assert_not_called()

    def test_rate_limit_retry_after_is_honored_without_another_request(self):
        api = Binance("dummy", "dummy")
        error = urllib.error.HTTPError(
            "https://api.binance.com", 429, "rate limited", {"Retry-After": "120"}, None
        )
        with patch("live_api.secure_json", side_effect=error) as network:
            for _ in range(2):
                with self.assertRaises(ExchangeError):
                    api.request("GET", "/api/v3/account")
            self.assertEqual(network.call_count, 1)

    def test_lost_initialized_ledger_cannot_allocate_again(self):
        class API:
            def preflight(self):
                return {"balances": []}

        with TemporaryDirectory(dir=TEST_TEMP) as folder:
            engine = Engine(
                Path(folder), API(), {"key": "dummy", "secret": "dummy", "initialized": True}
            )
            with self.assertRaises(ValueError):
                engine.initialize()

    def test_failed_durable_write_prevents_submission(self):
        from unittest.mock import Mock

        with TemporaryDirectory(dir=TEST_TEMP) as folder:
            api = Mock()
            engine = Engine(
                Path(folder), api, {"key": "dummy", "secret": "dummy", "installation": "test"}
            )
            engine.state = {"active": None, "halted": False, "last_signal": 0, "entries_today": 0}
            plan = plan_entry(80000, 79999, 100, 10, 0, ".001", rules())
            engine._approval = (
                100,
                hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                time.monotonic(),
            )
            with patch.object(engine.store, "write", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    engine.submit(plan, 100)
            api.request.assert_not_called()

    def test_signed_state_rejects_tampering(self):
        with TemporaryDirectory(dir=TEST_TEMP) as folder:
            store = StateStore(Path(folder), "dummy-secret")
            store.write({"cash": "10"})
            self.assertEqual(store.read()["cash"], "10")
            payload = json.loads(store.path.read_text())
            payload["state"]["cash"] = "1000"
            store.path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                store.read()

    def test_windows_encryption_roundtrip_does_not_store_plaintext(self):
        value = b"test-dummy-key-not-a-real-secret"
        encrypted = credential_store.protect(value)
        self.assertNotIn(value, encrypted)
        self.assertEqual(credential_store.protect(encrypted, decrypt=True), value)

    def test_fee_bound_includes_tax_and_special_commission(self):
        fee = fee_bound(
            {
                "standardCommission": {"taker": ".001", "buyer": ".0001", "seller": ".0002"},
                "taxCommission": {"taker": ".0001"},
                "specialCommission": {"taker": ".0002"},
            }
        )
        self.assertEqual(fee, number(".0015"))
        with self.assertRaises(ExchangeError):
            fee_bound({})

    def test_uncertain_post_persists_ids_and_never_retries(self):
        class API:
            def __init__(self):
                self.posts = 0

            def request(self, method, path, params):
                if method == "POST":
                    self.posts += 1
                    raise ExchangeError("network", uncertain=True)
                raise ExchangeError(-2013)

        with TemporaryDirectory(dir=TEST_TEMP) as folder:
            api = API()
            engine = Engine(
                Path(folder), api, {"secret": "dummy", "key": "dummy", "installation": "test"}
            )
            engine.state = {
                "cash": "10",
                "base": "0",
                "active": None,
                "halted": False,
                "last_signal": 0,
                "entries_today": 0,
                "cycles": [],
            }
            plan = plan_entry(80000, 79999, 100, 10, 0, ".001", rules())
            engine._approval = (
                100,
                hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
                time.monotonic(),
            )
            engine.submit(plan, 100)
            self.assertEqual(api.posts, 1)
            self.assertTrue(engine.state["halted"])
            self.assertIsNotNone(engine.store.read()["active"])
            engine.reconcile()
            engine.submit(plan, 200)
            self.assertEqual(api.posts, 1)
            self.assertEqual(engine.state["status"], "uncertain_order")

    def test_fill_reconciliation_is_idempotent_and_keeps_residual_in_budget(self):
        class API:
            closed = False

            def request(self, method, path, params):
                if path.endswith("/order"):
                    client = params["origClientOrderId"]
                    if client == "ct_buy":
                        return {
                            "clientOrderId": client,
                            "status": "FILLED",
                            "executedQty": ".00009",
                            "orderId": 1,
                            "side": "BUY",
                        }
                    if client == "ct_target":
                        return {
                            "clientOrderId": client,
                            "status": "FILLED" if self.closed else "NEW",
                            "executedQty": ".00008" if self.closed else "0",
                            "orderId": 2,
                            "side": "SELL",
                        }
                    return {
                        "clientOrderId": client,
                        "status": "EXPIRED" if self.closed else "NEW",
                        "executedQty": "0",
                        "orderId": 3,
                        "side": "SELL",
                    }
                if params["orderId"] == 1:
                    return [
                        {
                            "id": 10,
                            "qty": ".00009",
                            "quoteQty": "7.2",
                            "commission": ".00000009",
                            "commissionAsset": "BTC",
                        }
                    ]
                return [
                    {
                        "id": 11,
                        "qty": ".00008",
                        "quoteQty": "6.5",
                        "commission": ".0065",
                        "commissionAsset": "USDT",
                    }
                ]

        with TemporaryDirectory(dir=TEST_TEMP) as folder:
            api = API()
            engine = Engine(
                Path(folder), api, {"secret": "dummy", "key": "dummy", "installation": "test"}
            )
            cycle = {
                "buy_id": "ct_buy",
                "target_id": "ct_target",
                "stop_id": "ct_stop",
                "created": 0,
                "seen_trades": [],
            }
            engine.state = {
                "cash": "10",
                "base": "0",
                "active": cycle,
                "cycles": [],
                "halted": False,
            }
            engine.reconcile()
            engine.reconcile()
            self.assertEqual(number(engine.state["cash"]), number("2.8"))
            self.assertEqual(number(engine.state["base"]), number(".00008991"))
            self.assertEqual(cycle["protection"], "confirmed")
            api.closed = True
            engine.reconcile()
            engine.reconcile()
            self.assertEqual(number(engine.state["cash"]), number("9.2935"))
            self.assertEqual(number(engine.state["base"]), number(".00000991"))
            self.assertIsNone(engine.state["active"])


if __name__ == "__main__":
    unittest.main()
