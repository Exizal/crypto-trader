"""Budget-isolated BTCUSDT automation with Binance-hosted OTOCO exits.

Only the engine's atomic entry+stop+target order list can create orders.
Uncertain submissions are reconciled by persisted IDs, never retried.
"""

from decimal import Decimal as D, ROUND_DOWN, ROUND_UP
import hashlib
import hmac
import json
import math
import os
import threading
import time
import uuid
from datetime import datetime, timezone

import bot
import credential_store
from ai_review import Gate
from live_api import ExchangeError, fee_bound

SYMBOL = "BTCUSDT"
BUDGET = D("10")
POSITION_CAP = D("7.50")
RISK_CAP = D("0.10")


def number(value):
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("Non-finite amount")
    return result


def rounded(value, step, up=False):
    return (value / step).to_integral_value(rounding=ROUND_UP if up else ROUND_DOWN) * step


def decimal_text(value):
    return format(value, "f")


def plan_entry(ask, bid, atr, cash, owned, fee, info):
    """No increase to the budget or planned risk to satisfy an exchange minimum."""
    ask, bid, atr, cash, owned, fee = map(number, (ask, bid, atr, cash, owned, fee))
    if not 0 < bid <= ask or atr <= 0 or cash <= 0 or owned < 0:
        return None
    if (ask - bid) / bid > D("0.001") or info.get("status") != "TRADING":
        return None
    if (
        not info.get("ocoAllowed")
        or not info.get("otoAllowed")
        or "STOP_LOSS" not in info.get("orderTypes", [])
    ):
        return None
    filters = {f["filterType"]: f for f in info["filters"]}
    lot, price_filter = filters["LOT_SIZE"], filters["PRICE_FILTER"]
    step, tick = number(lot["stepSize"]), number(price_filter["tickSize"])
    entry = rounded(ask * D("1.0005"), tick, True)
    stop = rounded(entry - 2 * atr, tick)
    if stop <= 0 or stop >= bid:
        return None
    target = rounded(entry + 2 * (entry - stop), tick, True)
    room = min(POSITION_CAP - owned * bid, cash / (1 + fee), BUDGET / (1 + fee))
    planned_unit_loss = (entry - stop) + entry * (2 * fee + D("0.0005"))
    quantity = rounded(min(room / entry, RISK_CAP / planned_unit_loss), step)
    # Reserve base-asset commission. Quantization leaves a small residual balance.
    exit_quantity = rounded(quantity * (1 - fee * D("1.1")), step)
    minimum = max(
        number(filters.get("NOTIONAL", {}).get("minNotional", 0)),
        number(filters.get("MIN_NOTIONAL", {}).get("minNotional", 0)),
    )
    if quantity < number(lot["minQty"]) or exit_quantity < number(lot["minQty"]):
        return None
    if (
        quantity > number(lot["maxQty"])
        or quantity * entry < minimum * D("1.10")
        or exit_quantity * stop < minimum * D("1.10")
    ):
        return None
    maximum = number(filters.get("NOTIONAL", {}).get("maxNotional", 0))
    if maximum and quantity * target > maximum:
        return None
    if quantity * entry * (1 + fee) > cash or quantity * entry + owned * bid > POSITION_CAP:
        return None
    return {
        k: decimal_text(v)
        for k, v in {
            "entry": entry,
            "stop": stop,
            "target": target,
            "quantity": quantity,
            "exit_quantity": exit_quantity,
            "planned_loss": quantity * planned_unit_loss,
            "residual_estimate": (quantity - exit_quantity) * entry,
        }.items()
    }


class StateStore:
    def __init__(self, root, secret):
        self.path, self.secret = root / "live_state.json", secret.encode()

    def tag(self, state, version=2):
        key = (
            hmac.new(self.secret, b"crypto-trader:ledger:v2", hashlib.sha256).digest()
            if version == 2
            else self.secret
        )
        return hmac.new(
            key, json.dumps(state, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
        ).hexdigest()

    def write(self, state):
        payload = {"state": state, "mac": self.tag(state), "version": 2}
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(payload, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(self.path)

    def read(self):
        if self.path.stat().st_size > 4_194_304:
            raise ValueError("Saved state exceeded the accepted size")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        version = payload.get("version", 1)
        if version not in (1, 2) or not hmac.compare_digest(
            payload["mac"], self.tag(payload["state"], version)
        ):
            raise ValueError("Saved live state failed integrity verification")
        return payload["state"]


class Engine:
    def __init__(self, root, api, connection, stop_event=None, store=None, reviewer=None):
        self.root, self.api, self.connection = root, api, connection
        self.stop_event = stop_event or threading.Event()
        self.store = store or StateStore(root, connection["secret"])
        self.state = None
        self.reviewer = reviewer or Gate(root)
        self._approval = None

    def save(self, status=None):
        if status:
            self.state["status"] = status
            if self.state.get("halted") and status not in (
                "paused",
                "waiting_signal",
                "active_position",
            ):
                self.state["halt_reason"] = status
        self.state["heartbeat_utc"] = datetime.now(timezone.utc).isoformat()
        self.store.write(self.state)

    def initialize(self, account=None):
        account = self.api.preflight() if account is None else account
        fingerprint = hashlib.sha256(self.connection["key"].encode()).hexdigest()
        if self.store.path.exists():
            self.state = self.store.read()
            if self.state["key_fingerprint"] != fingerprint or self.state["budget"] != "10":
                raise ValueError("Connection or budget mismatch")
            if (
                self.state.get("account_uid")
                and str(account.get("uid")) != self.state["account_uid"]
            ):
                raise ValueError("Account identity changed")
            if account.get("uid") is not None:
                self.state["account_uid"] = str(account["uid"])
            self.verify_known_orders()
        else:
            if self.connection.get("initialized"):
                raise ValueError("Live records missing; do not allocate a second budget")
            if any(
                o["clientOrderId"].startswith("ct_")
                for o in self.api.request("GET", "/api/v3/openOrders", {"symbol": SYMBOL})
            ):
                raise ValueError("Existing app orders require their original records")
            balances = {b["asset"]: b for b in account["balances"]}
            if number(balances.get("USDT", {}).get("free", 0)) < BUDGET:
                raise ExchangeError("no_funds")
            self.connection["initialized"] = True
            credential_store.save(self.root, self.connection)
            self.state = {
                "budget": "10",
                "cash": "10",
                "base": "0",
                "reserved_base": decimal_text(
                    number(balances.get("BTC", {}).get("free", 0))
                    + number(balances.get("BTC", {}).get("locked", 0))
                ),
                "key_fingerprint": fingerprint,
                "cycles": [],
                "active": None,
                "last_signal": 0,
                "account_uid": str(account.get("uid", "")),
                "day": "",
                "day_start": "10",
                "entries_today": 0,
                "peak": "10",
                "halted": False,
                "status": "waiting_signal",
                "last_bid": "0",
            }
            self.save()

    def verify_known_orders(self):
        known = set()
        for cycle in self.state["cycles"] + (
            [self.state["active"]] if self.state["active"] else []
        ):
            known.update(cycle[k] for k in ("buy_id", "target_id", "stop_id"))
        orders = self.api.request("GET", "/api/v3/allOrders", {"symbol": SYMBOL, "limit": 1000})
        opened = self.api.request("GET", "/api/v3/openOrders", {"symbol": SYMBOL})
        if any(
            o["clientOrderId"].startswith("ct_") and o["clientOrderId"] not in known
            for o in orders + opened
        ):
            raise ValueError("Untracked app order; saved state may be stale")

    def reconcile(self):
        cycle = self.state["active"]
        if cycle is None:
            return
        try:
            parent = self.api.request(
                "GET", "/api/v3/order", {"symbol": SYMBOL, "origClientOrderId": cycle["buy_id"]}
            )
        except ExchangeError as exc:
            if exc.code == -2013:
                self.state["halted"] = True
                self.save("uncertain_order")
                return  # Never resubmit an uncertain intent, including after restart.
            raise
        records = [parent]
        if (
            parent["status"] in ("EXPIRED", "REJECTED", "CANCELED")
            and number(parent["executedQty"]) == 0
        ):
            cycle["outcome"] = "not_filled"
            self.state["cycles"].append(cycle)
            self.state["active"] = None
            self.save("waiting_signal")
            return
        if parent["status"] == "FILLED":
            for order_id in (cycle["target_id"], cycle["stop_id"]):
                records.append(
                    self.api.request(
                        "GET", "/api/v3/order", {"symbol": SYMBOL, "origClientOrderId": order_id}
                    )
                )
        elif time.time() - cycle["created"] > 60:
            self.state["halted"] = True
            self.save("check_exchange")
            return
        for order in records:
            if number(order["executedQty"]) <= 0:
                continue
            trades = self.api.request(
                "GET",
                "/api/v3/myTrades",
                {"symbol": SYMBOL, "orderId": order["orderId"], "limit": 1000},
            )
            if not trades:
                raise ExchangeError("fills_pending")
            if sum(number(t["qty"]) for t in trades) != number(order["executedQty"]):
                raise ExchangeError("fills_pending")
            for trade in trades:
                identifier = str(trade["id"])
                if identifier in cycle["seen_trades"]:
                    continue
                quantity, quote, fee = (
                    number(trade["qty"]),
                    number(trade["quoteQty"]),
                    number(trade["commission"]),
                )
                if quantity < 0 or quote < 0 or fee < 0:
                    raise ValueError("Invalid fill data")
                cash, base = number(self.state["cash"]), number(self.state["base"])
                if order["side"] == "BUY":
                    cash, base = cash - quote, base + quantity
                else:
                    cash, base = cash + quote, base - quantity
                asset = trade["commissionAsset"]
                if asset == "BTC":
                    base -= fee
                elif asset == "USDT":
                    cash -= fee
                elif fee:
                    # Count BNB fees against the isolated budget even though Binance
                    # charged another asset. Unknown fee assets stop accounting.
                    if asset != "BNB":
                        raise ExchangeError("fee_asset")
                    price = bot.request_json("/api/v3/ticker/price", {"symbol": "BNBUSDT"})
                    cash -= fee * number(price["price"])
                if cash < -D("0.000001") or base < -D("0.000000000001"):
                    raise ValueError("Budget accounting invalid; no further orders")
                self.state["cash"], self.state["base"] = (
                    decimal_text(cash),
                    decimal_text(max(base, D(0))),
                )
                cycle["seen_trades"].append(identifier)
                self.save("active_position")
        if parent["status"] == "FILLED":
            exits = records[1:]
            working = any(o["status"] in ("NEW", "PARTIALLY_FILLED", "PENDING_NEW") for o in exits)
            protection = any(
                o["clientOrderId"] == cycle["stop_id"]
                and o["status"] in ("NEW", "PARTIALLY_FILLED")
                for o in exits
            )
            cycle["protection"] = "confirmed" if protection else "pending"
            if not working:
                if not any(number(o["executedQty"]) > 0 for o in exits):
                    self.state["halted"] = True
                    self.save("check_exchange")
                    return
                cycle["outcome"] = "closed"
                self.state["cycles"].append(cycle)
                self.state["active"] = None
                self.save("waiting_signal")
            elif not protection and time.time() - cycle["created"] > 30:
                self.state["halted"] = True
                self.save("check_exchange")
            else:
                self.save("active_position")

    def submit(self, plan, signal_timestamp):
        if (
            self.stop_event.is_set()
            or self.state["halted"]
            or self.state["active"] is not None
            or signal_timestamp <= self.state["last_signal"]
        ):
            return
        digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        approval, self._approval = self._approval, None
        if (
            not approval
            or approval[0] != signal_timestamp
            or approval[1] != digest
            or time.monotonic() - approval[2] > 60
        ):
            self.save("ai_unconfigured")
            return
        tag = "ct_" + self.connection["installation"] + "_" + uuid.uuid4().hex[:8]
        cycle = {
            "list_id": tag,
            "buy_id": tag + "b",
            "target_id": tag + "t",
            "stop_id": tag + "s",
            "plan": plan,
            "seen_trades": [],
            "created": time.time(),
            "outcome": "intent",
        }
        self.state["active"] = cycle
        self.state["last_signal"] = signal_timestamp
        self.state["entries_today"] += 1
        self.save("submitting")  # Durable intent BEFORE the only mutation request.
        if self.stop_event.is_set():
            self.state["active"] = None
            self.save("paused")
            return
        params = {
            "symbol": SYMBOL,
            "listClientOrderId": tag,
            "workingType": "LIMIT",
            "workingSide": "BUY",
            "workingTimeInForce": "FOK",
            "workingClientOrderId": cycle["buy_id"],
            "workingPrice": plan["entry"],
            "workingQuantity": plan["quantity"],
            "pendingSide": "SELL",
            "pendingQuantity": plan["exit_quantity"],
            "pendingAboveType": "LIMIT_MAKER",
            "pendingAboveClientOrderId": cycle["target_id"],
            "pendingAbovePrice": plan["target"],
            "pendingBelowType": "STOP_LOSS",
            "pendingBelowClientOrderId": cycle["stop_id"],
            "pendingBelowStopPrice": plan["stop"],
        }
        try:
            self.api.request("POST", "/api/v3/orderList/otoco", params)
            cycle["outcome"] = "accepted"
            self.save("active_position")
        except ExchangeError as exc:
            if exc.uncertain:
                cycle["outcome"] = "uncertain"
                self.state["halted"] = True
                self.save("uncertain_order")
            else:
                cycle["outcome"] = "rejected"
                self.state["cycles"].append(cycle)
                self.state["active"] = None
                self.state["halted"] = True
                self.save("order_rejected")

    def tick(self):
        self.reconcile()
        if self.stop_event.is_set():
            return
        quote_started = time.time()
        account = self.api.request("GET", "/api/v3/account")
        book = bot.request_json("/api/v3/ticker/bookTicker", {"symbol": SYMBOL})
        bid, ask = number(book["bidPrice"]), number(book["askPrice"])
        if not 0 < bid <= ask or time.time() - quote_started > 20:
            raise ExchangeError("stale_data")
        self.state["last_bid"] = decimal_text(bid)
        equity = number(self.state["cash"]) + number(self.state["base"]) * bid
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self.state["day"]:
            self.state.update(day=today, day_start=decimal_text(equity), entries_today=0)
        self.state["peak"] = decimal_text(max(number(self.state["peak"]), equity))
        if equity <= number(self.state["day_start"]) * D("0.98") or equity <= number(
            self.state["peak"]
        ) * D("0.90"):
            self.state["halted"] = True
            self.save("risk_halt")
        if (
            self.state["halted"]
            or self.state["active"] is not None
            or self.state["entries_today"] >= 3
        ):
            self.save()
            return
        if not account.get("canTrade"):
            raise ExchangeError("permissions")
        balances = {b["asset"]: b for b in account["balances"]}
        actual_base = number(balances.get("BTC", {}).get("free", 0)) + number(
            balances.get("BTC", {}).get("locked", 0)
        )
        if actual_base + D("0.000000000001") < number(self.state["reserved_base"]) + number(
            self.state["base"]
        ):
            self.state["halted"] = True
            self.save("check_exchange")
            return
        end = int(time.time() * 1000) // 3_600_000 * 3_600_000 - 1
        candles = bot.get_candles(end - 300 * 3_600_000 + 1, end)
        if (
            len(candles) < 200
            or candles[-1].timestamp + 3_600_000 > int(time.time() * 1000)
            or int(time.time() * 1000) - candles[-1].timestamp > 7_200_000
        ):
            raise ExchangeError("stale_data")
        if candles[-1].timestamp <= self.state["last_signal"]:
            self.save("waiting_signal")
            return
        fast, slow, atr = bot.indicators(candles)
        if not fast[-1] > slow[-1] or not fast[-2] <= slow[-2] or not math.isfinite(atr[-1]):
            self.state["last_signal"] = candles[-1].timestamp
            self.save("waiting_signal")
            return
        info = bot.request_json("/api/v3/exchangeInfo", {"symbol": SYMBOL})["symbols"][0]
        commission = self.api.request("GET", "/api/v3/account/commission", {"symbol": SYMBOL})
        fee = fee_bound(commission)
        available = min(number(self.state["cash"]), number(balances.get("USDT", {}).get("free", 0)))
        plan = plan_entry(ask, bid, atr[-1], available, self.state["base"], fee, info)
        if plan is None:
            self.state["last_signal"] = candles[-1].timestamp
            self.save("minimum_order")
            return
        self.save("ai_reviewing")
        snapshot = {
            "symbol": SYMBOL,
            "signal_timestamp": candles[-1].timestamp,
            "bid": float(bid),
            "ask": float(ask),
            "ema_fast": fast[-1],
            "ema_slow": slow[-1],
            "atr": atr[-1],
            **{
                key: float(plan[key])
                for key in ("entry", "stop", "target", "quantity", "planned_loss")
            },
        }
        verdict = self.reviewer.review(snapshot)
        self.state["last_ai"] = {
            k: verdict[k] for k in ("status", "reason", "model") if k in verdict
        }
        if not verdict.get("approved"):
            self.state["last_signal"] = candles[-1].timestamp
            self.save(verdict.get("status", "ai_wait"))
            return
        self._approval = (
            candles[-1].timestamp,
            hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
            time.monotonic(),
        )
        # Candle download/account checks can take time: refresh the bid/ask and
        # reject a stale plan, rather than knowingly sending a stale entry.
        fresh = bot.request_json("/api/v3/ticker/bookTicker", {"symbol": SYMBOL})
        if number(fresh["askPrice"]) > number(plan["entry"]) or number(fresh["bidPrice"]) <= number(
            plan["stop"]
        ):
            self.state["last_signal"] = candles[-1].timestamp
            self.save("stale_data")
            return
        if datetime.now(timezone.utc).date().isoformat() != self.state["day"]:
            self.state["last_signal"] = candles[-1].timestamp
            self.save("stale_data")
            return
        fresh_account = self.api.request("GET", "/api/v3/account")
        fresh_balances = {b["asset"]: b for b in fresh_account["balances"]}
        actual_base = number(fresh_balances.get("BTC", {}).get("free", 0)) + number(
            fresh_balances.get("BTC", {}).get("locked", 0)
        )
        if actual_base + D("0.000000000001") < number(self.state["reserved_base"]) + number(
            self.state["base"]
        ):
            self.state["halted"] = True
            self.save("check_exchange")
            return
        if number(fresh_balances.get("USDT", {}).get("free", 0)) < number(
            plan["quantity"]
        ) * number(plan["entry"]) * (1 + fee):
            self.state["last_signal"] = candles[-1].timestamp
            self.save("minimum_order")
            return
        self.submit(plan, candles[-1].timestamp)

    def run(self):
        # Cross-folder copies using the same key cannot trade concurrently.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        account = self.api.preflight()
        uid = str(account.get("uid", ""))
        if not uid.isdecimal() or len(uid) > 32:
            raise ValueError("Verified Binance account identity is required")
        names = [
            "Local\\CryptoTrader_" + hashlib.sha256(self.connection["key"].encode()).hexdigest(),
            "Global\\CryptoTraderAccount_" + hashlib.sha256(uid.encode()).hexdigest(),
        ]
        handles = []
        try:
            for name in names:
                ctypes.set_last_error(0)
                handle = kernel.CreateMutexW(None, False, name)
                if not handle or ctypes.get_last_error() == 183:
                    if handle:
                        kernel.CloseHandle(handle)
                    raise RuntimeError("Another instance owns this account")
                handles.append(handle)
            self.initialize(account)
            count = 0
            while not self.stop_event.is_set():
                try:
                    if count % 30 == 0:
                        self.api.preflight()
                    self.tick()
                    count += 1
                except ExchangeError as exc:
                    # Reading a failed response never creates a new order.
                    # Persist pending intent and let subsequent cycles reconcile.
                    if exc.code in ("permissions", "fee_high", "fee_asset") or exc.code in (
                        -2014,
                        -2015,
                    ):
                        self.state["halted"] = True
                    self.save("connection_error" if not self.state["halted"] else "check_exchange")
                except Exception:
                    self.state["halted"] = True
                    self.save("check_exchange")
                self.stop_event.wait(20)
            self.save("paused")
        finally:
            for handle in reversed(handles):
                kernel.CloseHandle(handle)
