"""Market data, indicators and simulation utilities."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from secure_transport import secure_json

ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
BASE = "https://data-api.binance.vision"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
FAST, SLOW, ATR_PERIOD = 20, 50, 14


@dataclass
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Config:
    fee_rate: float = 0.001
    slippage: float = 0.0005
    risk_fraction: float = 0.01
    max_position_fraction: float = 0.50
    daily_loss_fraction: float = 0.02
    max_drawdown_fraction: float = 0.10
    max_entries_per_day: int = 3


def request_json(path: str, params: dict[str, Any] | None = None) -> Any:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "small-budget-paper-bot/1.0"})
    try:
        return secure_json(req, timeout=15, allowed_hosts=frozenset({"data-api.binance.vision"}))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Public market-data request failed ({url}): {exc}") from exc


def get_candles(start_ms: int | None = None, end_ms: int | None = None) -> list[Candle]:
    out: list[Candle] = []
    cursor = start_ms
    while True:
        params: dict[str, Any] = {"symbol": SYMBOL, "interval": INTERVAL, "limit": 1000}
        if cursor is not None:
            params["startTime"] = cursor
        if end_ms is not None:
            params["endTime"] = end_ms
        rows = request_json("/api/v3/klines", params)
        if not rows:
            break
        out.extend(
            Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            for r in rows
        )
        next_cursor = int(rows[-1][0]) + 3_600_000
        if len(rows) < 1000 or (end_ms is not None and next_cursor > end_ms):
            break
        if cursor is not None and next_cursor <= cursor:
            raise RuntimeError("Candle pagination did not advance")
        cursor = next_cursor
        time.sleep(0.15)
    deduped = {c.timestamp: c for c in out}
    return [deduped[k] for k in sorted(deduped)]


def exchange_rules() -> dict[str, Any]:
    info = request_json("/api/v3/exchangeInfo", {"symbol": SYMBOL})
    symbol = info["symbols"][0]
    filters = {f["filterType"]: f for f in symbol["filters"]}
    lot = filters.get("LOT_SIZE", {})
    notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
    return {
        "symbol": SYMBOL,
        "status": symbol.get("status"),
        "filters": filters,
        "min_qty": float(lot.get("minQty", 0)),
        "step_size": float(lot.get("stepSize", 0)),
        "min_notional": float(notional.get("minNotional", 0)),
    }


def liquidity_snapshot() -> dict[str, Any]:
    book = request_json("/api/v3/ticker/bookTicker", {"symbol": SYMBOL})
    stats = request_json("/api/v3/ticker/24hr", {"symbol": SYMBOL})
    bid, ask = float(book["bidPrice"]), float(book["askPrice"])
    mid = (bid + ask) / 2
    return {
        "symbol": SYMBOL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "bid": bid,
        "ask": ask,
        "spread": ask - bid,
        "spread_bps": ((ask - bid) / mid * 10_000) if mid else None,
        "base_volume_24h": float(stats["volume"]),
        "quote_volume_24h": float(stats["quoteVolume"]),
    }


def save_candles(path: Path, candles: list[Candle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(candles[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(c) for c in candles)


def load_candles(path: Path) -> list[Candle]:
    with path.open(newline="", encoding="utf-8") as f:
        return [
            Candle(
                int(r["timestamp"]),
                float(r["open"]),
                float(r["high"]),
                float(r["low"]),
                float(r["close"]),
                float(r["volume"]),
            )
            for r in csv.DictReader(f)
        ]


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def indicators(candles: list[Candle]) -> tuple[list[float], list[float], list[float]]:
    closes = [c.close for c in candles]
    fast, slow = ema(closes, FAST), ema(closes, SLOW)
    trs = []
    for i, c in enumerate(candles):
        prev = candles[i - 1].close if i else c.close
        trs.append(max(c.high - c.low, abs(c.high - prev), abs(c.low - prev)))
    atr = [math.nan] * len(trs)
    if len(trs) >= ATR_PERIOD:
        atr[ATR_PERIOD - 1] = sum(trs[:ATR_PERIOD]) / ATR_PERIOD
        for i in range(ATR_PERIOD, len(trs)):
            atr[i] = (atr[i - 1] * (ATR_PERIOD - 1) + trs[i]) / ATR_PERIOD
    return fast, slow, atr


def qty_for_entry(
    equity: float,
    cash: float,
    price: float,
    stop_distance: float,
    rules: dict[str, Any],
    cfg: Config,
) -> float:
    if min(equity, cash, price, stop_distance) <= 0:
        return 0.0
    risk_qty = equity * cfg.risk_fraction / stop_distance
    cap_qty = min(cash, equity * cfg.max_position_fraction) / price
    qty = min(risk_qty, cap_qty)
    step = rules.get("step_size", 0.0)
    if step > 0:
        qty = math.floor(qty / step) * step
    notional = qty * price
    if qty < rules.get("min_qty", 0) or notional < rules.get("min_notional", 0):
        return 0.0
    return qty


def backtest(
    candles: list[Candle],
    initial_cash: float = 10.0,
    cfg: Config | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg, rules = cfg or Config(), rules or {"min_qty": 0, "step_size": 0, "min_notional": 0}
    if len(candles) < SLOW + 2:
        raise ValueError(f"Need at least {SLOW + 2} hourly candles; got {len(candles)}")
    fast, slow, atr = indicators(candles)
    cash, qty, entry, stop = initial_cash, 0.0, 0.0, 0.0
    peak = initial_cash
    day_start = initial_cash
    current_day = ""
    entries_today = 0
    halted = False
    fees = 0.0
    trades: list[dict[str, Any]] = []
    equity_curve = [initial_cash]
    for i in range(SLOW, len(candles) - 1):
        c = candles[i]
        next_open = candles[i + 1].open
        day = datetime.fromtimestamp(c.timestamp / 1000, timezone.utc).date().isoformat()
        equity_before = cash + qty * c.close
        if day != current_day:
            current_day, day_start, entries_today = day, equity_before, 0
        peak = max(peak, equity_before)
        if equity_before <= day_start * (1 - cfg.daily_loss_fraction) or equity_before <= peak * (
            1 - cfg.max_drawdown_fraction
        ):
            halted = True
        cross_up = fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]
        cross_down = fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]
        entered_this_bar = False
        if qty > 0 and c.low <= stop:
            exit_price = min(c.open, stop) * (1 - cfg.slippage)
            proceeds = qty * exit_price
            fee = proceeds * cfg.fee_rate
            cash += proceeds - fee
            fees += fee
            trades.append(
                {"entry": entry, "exit": exit_price, "qty": qty, "fee": fee, "reason": "atr_stop"}
            )
            qty, stop = 0.0, 0.0
        elif qty > 0 and cross_down:
            exit_price = next_open * (1 - cfg.slippage)
            proceeds = qty * exit_price
            fee = proceeds * cfg.fee_rate
            cash += proceeds - fee
            fees += fee
            trades.append(
                {"entry": entry, "exit": exit_price, "qty": qty, "fee": fee, "reason": "ema_exit"}
            )
            qty, stop = 0.0, 0.0
        elif (
            not halted
            and qty == 0
            and entries_today < cfg.max_entries_per_day
            and cross_up
            and not math.isnan(atr[i])
        ):
            price = next_open * (1 + cfg.slippage)
            equity = cash
            amount = qty_for_entry(equity, cash, price, 2 * atr[i], rules, cfg)
            if amount > 0:
                cost = amount * price
                fee = cost * cfg.fee_rate
                if cost + fee <= cash:
                    cash -= cost + fee
                    fees += fee
                    qty, entry, stop = amount, price, price - 2 * atr[i]
                    entries_today += 1
                    entered_this_bar = True
        # A signal fills at the next bar's open; do not mark that new position
        # against the preceding bar's close.
        equity = cash + qty * (next_open if entered_this_bar else c.close)
        peak = max(peak, equity)
        equity_curve.append(equity)
    if qty > 0:
        px = candles[-1].close * (1 - cfg.slippage)
        proceeds, fee = qty * px, qty * px * cfg.fee_rate
        cash += proceeds - fee
        fees += fee
        trades.append({"entry": entry, "exit": px, "qty": qty, "fee": fee, "reason": "end_of_data"})
    final_equity = cash
    drawdown = max((1 - value / max(equity_curve[: i + 1])) for i, value in enumerate(equity_curve))
    return {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "candles": len(candles),
        "start_utc": datetime.fromtimestamp(candles[0].timestamp / 1000, timezone.utc).isoformat(),
        "end_utc": datetime.fromtimestamp(candles[-1].timestamp / 1000, timezone.utc).isoformat(),
        "initial_cash": initial_cash,
        "final_equity": final_equity,
        "return_pct": (final_equity / initial_cash - 1) * 100,
        "max_drawdown_pct": drawdown * 100,
        "closed_trades": len(trades),
        "fees_paid": fees,
        "assumptions": asdict(cfg),
        "venue_min_notional": rules.get("min_notional", 0),
        "trades": trades,
    }


def new_paper_state(initial_cash: float) -> dict[str, Any]:
    return {
        "cash": initial_cash,
        "qty": 0.0,
        "entry": 0.0,
        "stop": 0.0,
        "peak": initial_cash,
        "day": "",
        "day_start": initial_cash,
        "entries_today": 0,
        "last_signal_candle": 0,
        "halted": False,
    }


def paper_cycle(state, candles, bid, ask, rules, cfg, now_ms):
    """Consume closed candles and a newly fetched quote; never fill at an old candle price."""
    if len(candles) < SLOW + 2 or not 0 < bid <= ask:
        raise RuntimeError("Insufficient candles or invalid market quote")
    c = candles[-1]
    if not c.timestamp + 3_600_000 <= now_ms < c.timestamp + 7_200_000:
        raise RuntimeError("Market candles are stale or unclosed; paper trading paused")
    fast, slow, atr = indicators(candles)
    day = datetime.fromtimestamp(now_ms / 1000, timezone.utc).date().isoformat()
    equity = state["cash"] + state["qty"] * bid
    if day != state["day"]:
        state["day"], state["day_start"], state["entries_today"] = day, equity, 0
    state["peak"] = max(state["peak"], equity)
    new_signal = state["last_signal_candle"] != c.timestamp
    loss_limit = equity <= state["day_start"] * (1 - cfg.daily_loss_fraction) or equity <= state[
        "peak"
    ] * (1 - cfg.max_drawdown_fraction)
    if loss_limit:
        state["halted"] = True
    reason = None
    if state["qty"] > 0:
        if loss_limit:
            reason = "loss_limit"
        elif bid <= state["stop"]:
            reason = "atr_stop"
        elif new_signal and fast[-1] < slow[-1] and fast[-2] >= slow[-2]:
            reason = "ema_exit"
        if reason:
            px = bid * (1 - cfg.slippage)
            state["cash"] += state["qty"] * px * (1 - cfg.fee_rate)
            state["qty"], state["entry"], state["stop"] = 0.0, 0.0, 0.0
    elif (
        new_signal
        and not state["halted"]
        and state["entries_today"] < cfg.max_entries_per_day
        and rules.get("status") == "TRADING"
    ):
        if fast[-1] > slow[-1] and fast[-2] <= slow[-2] and not math.isnan(atr[-1]):
            px = ask * (1 + cfg.slippage)
            qty = qty_for_entry(state["cash"], state["cash"], px, 2 * atr[-1], rules, cfg)
            cost = qty * px * (1 + cfg.fee_rate)
            if qty > 0 and cost <= state["cash"]:
                state["cash"] -= cost
                state["qty"], state["entry"], state["stop"] = qty, px, px - 2 * atr[-1]
                state["entries_today"] += 1
                reason = "entry"
            else:
                reason = "entry_skipped_minimum_or_cash"
    state["last_signal_candle"] = c.timestamp
    state["heartbeat_utc"] = datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat()
    return reason or "monitoring"


def paper_loop(initial_cash: float, cfg: Config, rules: dict[str, Any], stop_file: Path) -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        filename=log_dir / "paper.log",
        level=logging.INFO,
        format="%(asctime)sZ %(levelname)s %(message)s",
    )
    state_path = ROOT / "paper_state.json"
    state = (
        json.loads(state_path.read_text()) if state_path.exists() else new_paper_state(initial_cash)
    )
    print("Paper mode. Ctrl+C stops. Create STOP in this folder to halt the monitor.", flush=True)
    while True:
        if stop_file.exists():
            state["halted"] = True
            state_path.write_text(json.dumps(state, indent=2))
            logging.warning("STOP detected; paper process exits. No real orders exist.")
            return
        try:
            now_ms = int(time.time() * 1000)
            end_ms = now_ms // 3_600_000 * 3_600_000 - 1
            candles = get_candles(end_ms - 300 * 3_600_000 + 1, end_ms)
            rules = exchange_rules()
            book = request_json("/api/v3/ticker/bookTicker", {"symbol": SYMBOL})
            quote_time = int(time.time() * 1000)
            if quote_time - now_ms > 30_000:
                raise RuntimeError("Market snapshot took too long; no paper action")
            action = paper_cycle(
                state,
                candles,
                float(book["bidPrice"]),
                float(book["askPrice"]),
                rules,
                cfg,
                quote_time,
            )
            temporary = state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, indent=2))
            temporary.replace(state_path)
            logging.info(
                "action=%s cash=%.6f qty=%.8f halted=%s",
                action,
                state["cash"],
                state["qty"],
                state["halted"],
            )
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            logging.error("Data or state error; no simulated order: %s", type(exc).__name__)
        time.sleep(60)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch", help="Download historical candles and current public filters")
    f.add_argument("--days", type=int, default=365)
    b = sub.add_parser("backtest", help="Backtest a downloaded candle CSV")
    b.add_argument("--data", type=Path, default=ROOT / "data" / "BTCUSDT-1h.csv")
    b.add_argument("--cash", type=float, default=10.0)
    b.add_argument("--fee", type=float, default=0.001)
    b.add_argument("--slippage", type=float, default=0.0005)
    pp = sub.add_parser("paper", help="Run the paper monitor")
    pp.add_argument("--cash", type=float, default=10.0)
    pp.add_argument("--fee", type=float, default=0.001)
    pp.add_argument("--slippage", type=float, default=0.0005)
    args = p.parse_args()
    if args.command == "fetch":
        if args.days < 30:
            p.error("--days must be at least 30")
        end = int(time.time() * 1000) // 3_600_000 * 3_600_000 - 1
        start = end - args.days * 86_400_000
        candles = get_candles(start, end)
        if len(candles) < SLOW + 2:
            raise RuntimeError("Downloaded data is too short to backtest")
        data = ROOT / "data"
        save_candles(data / "BTCUSDT-1h.csv", candles)
        rules = exchange_rules()
        liquidity = liquidity_snapshot()
        (data / "exchange_rules.json").write_text(json.dumps(rules, indent=2))
        (data / "liquidity_snapshot.json").write_text(json.dumps(liquidity, indent=2))
        (data / "source.json").write_text(
            json.dumps(
                {
                    "source": BASE,
                    "endpoint": "/api/v3/klines",
                    "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "symbol": SYMBOL,
                    "interval": INTERVAL,
                    "candle_count": len(candles),
                    "start_utc": datetime.fromtimestamp(
                        candles[0].timestamp / 1000, timezone.utc
                    ).isoformat(),
                    "end_utc": datetime.fromtimestamp(
                        candles[-1].timestamp / 1000, timezone.utc
                    ).isoformat(),
                },
                indent=2,
            )
        )
        print(f"Saved {len(candles)} candles and current public symbol rules to {data}")
        print(
            f"Current spread: {liquidity['spread_bps']:.2f} bps; 24h quote volume: {liquidity['quote_volume_24h']:.2f} USDT"
        )
    elif args.command == "backtest":
        candles = load_candles(args.data)
        rules_path = ROOT / "data" / "exchange_rules.json"
        rules = (
            json.loads(rules_path.read_text())
            if rules_path.exists()
            else {"min_qty": 0, "step_size": 0, "min_notional": 0}
        )
        report = backtest(
            candles, args.cash, Config(fee_rate=args.fee, slippage=args.slippage), rules
        )
        out = ROOT / "data" / "backtest_report.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(json.dumps({k: v for k, v in report.items() if k != "trades"}, indent=2))
        print(f"Full trade log: {out}")
    elif args.command == "paper":
        paper_loop(
            args.cash,
            Config(fee_rate=args.fee, slippage=args.slippage),
            exchange_rules(),
            ROOT / "STOP",
        )


if __name__ == "__main__":
    main()
