"""OpenAI entry reviews. The model can veto a candidate; it cannot create orders."""

from datetime import datetime, timezone
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

import credential_store
from secure_transport import secure_json

DEFAULT_MODEL = "gpt-6-luna"
MAX_CALLS_DAY = 6
MAX_OUTPUT_TOKENS = 512

SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "wait"]},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "reason": {"type": "string", "maxLength": 240},
    },
    "required": ["decision", "confidence", "reason"],
    "additionalProperties": False,
}


def model_valid(model):
    return isinstance(model, str) and bool(re.fullmatch(r"gpt-[a-z0-9.-]{1,60}", model))


def read_settings(root):
    path = root / ".private" / "ai.bin"
    if not path.exists():
        return None
    value = json.loads(credential_store.protect(path.read_bytes(), decrypt=True))
    if not model_valid(value.get("model")) or not isinstance(value.get("key"), str):
        raise ValueError("Invalid AI connection")
    return value


def save_settings(root, record):
    folder = root / ".private"
    folder.mkdir(exist_ok=True)
    path = folder / "ai.bin"
    temporary = folder / "ai.tmp"
    with temporary.open("wb") as output:
        output.write(credential_store.protect(json.dumps(record).encode()))
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)


def configure(root, key, model):
    if (
        not model_valid(model)
        or not isinstance(key, str)
        or not 20 <= len(key.strip()) <= 512
        or any(c.isspace() for c in key.strip())
    ):
        raise ValueError("Invalid API key or model")
    request = urllib.request.Request(
        "https://api.openai.com/v1/models/" + model,
        headers={"Authorization": "Bearer " + key.strip()},
    )
    try:
        result = secure_json(request)
        if result.get("id") != model:
            raise ValueError("Model not available")
    except Exception:
        raise RuntimeError("AI connection could not be verified") from None
    previous = read_settings(root) or {}
    record = {
        "key": key.strip(),
        "model": model,
        "day": previous.get("day", ""),
        "calls": previous.get("calls", 0),
        "reviews": previous.get("reviews", {}),
    }
    save_settings(root, record)


def snapshot_digest(snapshot):
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_snapshot(snapshot):
    import math

    required = {
        "symbol",
        "signal_timestamp",
        "bid",
        "ask",
        "ema_fast",
        "ema_slow",
        "atr",
        "entry",
        "stop",
        "target",
        "quantity",
        "planned_loss",
    }
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != required
        or snapshot["symbol"] != "BTCUSDT"
    ):
        raise ValueError("Only the permitted market snapshot may be sent")
    for key in required - {"symbol"}:
        value = snapshot[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError("Non-numeric market snapshot")
    raw = json.dumps(snapshot, allow_nan=False)
    if len(raw.encode()) > 6000:
        raise ValueError("Snapshot is too large")
    return raw


def parse_response(response):
    if not isinstance(response, dict) or response.get("status") != "completed":
        return None
    texts = []
    for item in response.get("output", []):
        if item.get("type") == "reasoning":
            continue
        if item.get("type") != "message":
            return None
        for part in item.get("content", []):
            if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                return None
            texts.append(part["text"])
    try:
        value = json.loads("".join(texts))
        if set(value) != {"decision", "confidence", "reason"} or value["decision"] not in (
            "approve",
            "wait",
        ):
            return None
        if (
            type(value["confidence"]) is not int
            or not 0 <= value["confidence"] <= 100
            or not isinstance(value["reason"], str)
            or len(value["reason"]) > 240
        ):
            return None
        value["reason"] = "".join(c for c in value["reason"] if c.isprintable())
        return value
    except (ValueError, TypeError, KeyError):
        return None


class Gate:
    def __init__(self, root):
        self.root = root

    def review(self, snapshot):
        raw = validate_snapshot(snapshot)
        record = read_settings(self.root)
        if record is None:
            return {"approved": False, "status": "ai_unconfigured"}
        day = datetime.now(timezone.utc).date().isoformat()
        if record.get("day") != day:
            record.update(day=day, calls=0, reviews={})
        fingerprint = record["model"] + ":" + str(snapshot["signal_timestamp"])
        digest = snapshot_digest(snapshot)
        cached = record["reviews"].get(fingerprint)
        if cached:
            # A pending/failed request is not retried after a timeout or restart.
            if time.time() - cached["created"] > 60 or cached.get("snapshot") != digest:
                return {"approved": False, "status": "ai_stale"}
            return cached["result"]
        if record["calls"] >= MAX_CALLS_DAY:
            return {"approved": False, "status": "ai_limit"}
        record["calls"] += 1
        entry = {
            "created": time.time(),
            "snapshot": digest,
            "result": {"approved": False, "status": "ai_error"},
        }
        record["reviews"][fingerprint] = entry
        save_settings(self.root, record)  # Reserve usage before a potentially billable request.
        payload = {
            "model": record["model"],
            "store": False,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none"},
            "instructions": "Review a fixed BTCUSDT Spot entry proposal for execution quality and uncertainty. You cannot change its prices, size or risk controls. Do not claim profit predictions. Approve only if the numeric context is internally consistent and supports the proposed trend entry; otherwise choose wait. Confidence is a review score, not a probability of profit. Keep the reason concise.",
            "input": [{"role": "user", "content": raw}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "entry_review",
                    "strict": True,
                    "schema": SCHEMA,
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            method="POST",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer " + record["key"],
                "Content-Type": "application/json",
            },
        )
        try:
            response = secure_json(request, timeout=20, max_bytes=131072)
            verdict = parse_response(response)
            if verdict is not None:
                entry["result"] = {
                    "approved": verdict["decision"] == "approve" and verdict["confidence"] >= 80,
                    "status": "ai_approved"
                    if verdict["decision"] == "approve" and verdict["confidence"] >= 80
                    else "ai_wait",
                    "reason": verdict["reason"],
                    "model": record["model"],
                }
        except Exception:
            entry["result"] = {"approved": False, "status": "ai_error"}
        save_settings(self.root, record)
        return entry["result"]
