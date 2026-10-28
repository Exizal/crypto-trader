"""Interactive Binance.com connection check. GET requests only; no order endpoint."""

import argparse
import getpass
import hashlib
import hmac
import time
import urllib.error
import urllib.parse
import urllib.request
from secure_transport import secure_json

HOST = "https://api.binance.com"
READ_ENDPOINTS = {
    "/api/v3/account",
    "/sapi/v1/account/apiRestrictions",
    "/api/v3/account/commission",
}


def signed_get(path, key, secret, params=None, offset_ms=0):
    if path not in READ_ENDPOINTS:
        raise ValueError("Only the approved account-reading endpoints are supported")
    values = dict(params or {})
    values.update(timestamp=int(time.time() * 1000) + offset_ms, recvWindow=5000)
    query = urllib.parse.urlencode(values)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        HOST + path + "?" + query + "&signature=" + signature,
        headers={"X-MBX-APIKEY": key},
        method="GET",
    )
    try:
        return secure_json(req, timeout=15)
    except urllib.error.HTTPError as exc:
        # Do not print the signed URL, response body, key, secret or account payload.
        raise RuntimeError(
            f"Binance rejected the connection check (HTTP {exc.code}). Check permissions, IP restrictions and system time."
        ) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Could not reach Binance. No orders were submitted.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--venue",
        choices=["binance-com"],
        required=True,
        help="This connector currently supports Binance.com only",
    )
    parser.parse_args()
    print("Binance.com connection check. Enter credentials in this local terminal only.")
    print("This check needs read access only. Credentials remain in memory for this process.")
    key = getpass.getpass("API key (hidden): ").strip()
    secret = getpass.getpass("API secret (hidden): ").strip()
    if not key or not secret:
        parser.exit(1, "Both fields are required. Nothing was saved.\n")
    try:
        response = secure_json(urllib.request.Request(HOST + "/api/v3/time"))
        offset = response["serverTime"] - int(time.time() * 1000)
        account = signed_get("/api/v3/account", key, secret, offset_ms=offset)
        permissions = signed_get("/sapi/v1/account/apiRestrictions", key, secret, offset_ms=offset)
        print("Connection verified. Account reading works.")
        print("IP restriction:", bool(permissions.get("ipRestrict")))
        print("Withdrawal permission:", bool(permissions.get("enableWithdrawals")))
        print("Spot trading permission:", bool(permissions.get("enableSpotAndMarginTrading")))
        print("Account trading eligibility:", bool(account.get("canTrade")))
        print("Live execution is not implemented or enabled in this prototype.")
    except (RuntimeError, urllib.error.URLError, TimeoutError):
        parser.exit(
            1,
            "Connection check failed. Confirm venue, API permissions, IP restrictions and network connection. No credentials were saved.\n",
        )


if __name__ == "__main__":
    main()
