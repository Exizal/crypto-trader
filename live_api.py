"""Restricted Binance.com Spot transport. No withdrawals, transfers or leverage endpoints."""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from secure_transport import secure_json


class ExchangeError(RuntimeError):
    def __init__(self, code, uncertain=False):
        self.code, self.uncertain = code, uncertain
        super().__init__(f"Binance request failed: code {code}; uncertain={uncertain}")


class Binance:
    HOST = "https://api.binance.com"
    READ = {
        "/api/v3/account",
        "/api/v3/account/commission",
        "/api/v3/order",
        "/api/v3/orderList",
        "/api/v3/myTrades",
        "/api/v3/openOrders",
        "/api/v3/allOrders",
        "/sapi/v1/account/apiRestrictions",
    }

    def __init__(self, key, secret, armed=False):
        self.key, self.secret, self.armed = key, secret, armed
        self.offset = 0
        self.blocked_until = 0

    def sync_time(self):
        response = secure_json(urllib.request.Request(self.HOST + "/api/v3/time"), timeout=10)
        self.offset = response["serverTime"] - int(time.time() * 1000)

    def request(self, method, path, params=None):
        if time.monotonic() < self.blocked_until:
            raise ExchangeError("rate_limited")
        if method == "GET":
            if path not in self.READ:
                raise ValueError("Read endpoint not permitted")
        elif method == "POST" and path == "/api/v3/orderList/otoco":
            if not self.armed:
                raise ValueError("Real trading has not been enabled")
            from decimal import Decimal

            order = params or {}
            required = {
                "symbol": "BTCUSDT",
                "workingSide": "BUY",
                "workingType": "LIMIT",
                "workingTimeInForce": "FOK",
                "pendingSide": "SELL",
                "pendingAboveType": "LIMIT_MAKER",
                "pendingBelowType": "STOP_LOSS",
            }
            if any(order.get(k) != v for k, v in required.items()):
                raise ValueError("Only the protected BTCUSDT entry is permitted")
            amount, price = Decimal(order["workingQuantity"]), Decimal(order["workingPrice"])
            stop, target = (
                Decimal(order["pendingBelowStopPrice"]),
                Decimal(order["pendingAbovePrice"]),
            )
            sell = Decimal(order["pendingQuantity"])
            if (
                not all(v.is_finite() for v in (amount, price, stop, target, sell))
                or not 0 < amount * price <= Decimal("7.5")
                or not 0 < sell <= amount
                or not 0 < stop < price < target
            ):
                raise ValueError("Order exceeds the fixed limits")
            if any(
                not order.get(k, "").startswith("ct_")
                for k in (
                    "listClientOrderId",
                    "workingClientOrderId",
                    "pendingAboveClientOrderId",
                    "pendingBelowClientOrderId",
                )
            ):
                raise ValueError("Order identifiers are required")
        else:
            raise ValueError("Endpoint or method not permitted")
        values = dict(params or {})
        values.update(timestamp=int(time.time() * 1000) + self.offset, recvWindow=5000)
        query = urllib.parse.urlencode(values)
        signature = hmac.new(self.secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        payload = (query + "&signature=" + signature).encode()
        url = self.HOST + path
        if method == "GET":
            url += "?" + payload.decode()
        request = urllib.request.Request(
            url,
            data=payload if method == "POST" else None,
            method=method,
            headers={"X-MBX-APIKEY": self.key, "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            return secure_json(request, timeout=15)
        except urllib.error.HTTPError as exc:
            if exc.code in (418, 429):
                try:
                    delay = max(1, int(exc.headers.get("Retry-After", "60")))
                except (TypeError, ValueError):
                    delay = 60
                self.blocked_until = time.monotonic() + delay
            code = exc.code
            try:
                code = json.loads(exc.read(4096)).get("code", code)
            except (ValueError, OSError):
                pass
            # Retain the durable intent for every failed mutation response.
            raise ExchangeError(code, method == "POST") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            # A network failure can occur after Binance accepted the request.
            # The engine must query the persisted IDs and never resend blindly.
            raise ExchangeError("network", method == "POST") from None

    def preflight(self):
        self.sync_time()
        account = self.request("GET", "/api/v3/account")
        permission = self.request("GET", "/sapi/v1/account/apiRestrictions")
        if (
            not account.get("canTrade")
            or not permission.get("enableReading")
            or not permission.get("enableSpotAndMarginTrading")
        ):
            raise ExchangeError("permissions")
        if (
            permission.get("enableWithdrawals") is not False
            or permission.get("ipRestrict") is not True
        ):
            raise ExchangeError("permissions")
        for flag in (
            "enableFutures",
            "enableMargin",
            "enableInternalTransfer",
            "permitsUniversalTransfer",
            "enablePortfolioMarginTrading",
        ):
            if permission.get(flag):
                raise ExchangeError("permissions")
        return account


def fee_bound(commission):
    """Upper bound ignoring BNB discounts, including special and tax commission."""
    from decimal import Decimal

    if not all(k in commission.get("standardCommission", {}) for k in ("taker", "buyer", "seller")):
        raise ExchangeError("fee_high")
    totals = []
    for side in ("buyer", "seller"):
        totals.append(
            sum(
                (
                    Decimal(str(commission.get(group, {}).get("taker", "0")))
                    + Decimal(str(commission.get(group, {}).get(side, "0")))
                )
                for group in ("standardCommission", "specialCommission", "taxCommission")
            )
        )
    value = max(totals)
    if value < 0 or value > Decimal("0.004"):
        # Zero-fee promotions are permitted; a missing standard group is not.
        if value != 0 or "standardCommission" not in commission:
            raise ExchangeError("fee_high")
    return value
