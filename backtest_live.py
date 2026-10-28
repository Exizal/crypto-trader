"""Historical approximation of the real engine's bracket strategy; no API calls."""

from decimal import Decimal as D
import json
from datetime import datetime, timezone

import bot
from live_engine import plan_entry, number, rounded


def run(candles, info, fee=D("0.001")):
    fast, slow, atr = bot.indicators(candles)
    cash, base, peak, day_start = D("10"), D(0), D("10"), D("10")
    active = None
    day, halted = "", False
    entries_today, fees = 0, D(0)
    trades, values, skipped = [], [10.0], 0
    filters = {f["filterType"]: f for f in info["filters"]}
    step = number(filters["LOT_SIZE"]["stepSize"])
    for i in range(200, len(candles)):
        c, prev = candles[i], candles[i - 1]
        date = datetime.fromtimestamp(c.timestamp / 1000, timezone.utc).date().isoformat()
        equity_open = cash + base * number(c.open)
        if date != day:
            day, day_start, entries_today = date, equity_open, 0
        peak = max(peak, equity_open)
        if equity_open <= day_start * D(".98") or equity_open <= peak * D(".90"):
            halted = True
        if (
            active is None
            and not halted
            and entries_today < 3
            and fast[i - 1] > slow[i - 1]
            and fast[i - 2] <= slow[i - 2]
        ):
            plan = plan_entry(c.open, c.open, atr[i - 1], cash, base, fee, info)
            if plan:
                q, px = number(plan["quantity"]), number(plan["entry"])
                charge = q * fee
                cash -= q * px
                base += q - charge
                fees += charge * px
                active = plan
                active["entry_utc"] = datetime.fromtimestamp(
                    c.timestamp / 1000, timezone.utc
                ).isoformat()
                entries_today += 1
            else:
                skipped += 1
        if active:
            stop, target = number(active["stop"]), number(active["target"])
            # Intrabar path is unknown. If both are touched, take the losing exit.
            exit_price = None
            if number(c.low) <= stop:
                exit_price = min(number(c.open), stop) * D(".9995")
                reason = "stop"
            elif number(c.high) >= target:
                exit_price, reason = target, "target"
            if exit_price is not None:
                qty = min(number(active["exit_quantity"]), rounded(base, step))
                gross = qty * exit_price
                cash += gross * (1 - fee)
                fees += gross * fee
                base -= qty
                trades.append(
                    {
                        **active,
                        "exit": str(exit_price),
                        "reason": reason,
                        "exit_utc": datetime.fromtimestamp(
                            c.timestamp / 1000, timezone.utc
                        ).isoformat(),
                    }
                )
                active = None
        value = cash + base * number(c.close)
        peak = max(peak, value)
        if value <= day_start * D(".98") or value <= peak * D(".90"):
            halted = True
        values.append(float(value))
    maximum, drawdown = values[0], 0
    for value in values:
        maximum = max(maximum, value)
        drawdown = max(drawdown, 1 - value / maximum)
    equity = cash + base * number(candles[-1].close)
    return {
        "strategy": "EMA20/50 entry; 2ATR stop; 2R target; fixed 10 USDT budget",
        "candles": len(candles),
        "start_utc": datetime.fromtimestamp(candles[0].timestamp / 1000, timezone.utc).isoformat(),
        "end_utc": datetime.fromtimestamp(candles[-1].timestamp / 1000, timezone.utc).isoformat(),
        "initial_equity": 10,
        "final_equity": float(equity),
        "cash": float(cash),
        "remaining_btc": float(base),
        "closed_trades": len(trades),
        "return_pct": float((equity / D("10") - 1) * 100),
        "max_drawdown_pct": drawdown * 100,
        "fees_paid": float(fees),
        "minimum_skips": skipped,
        "risk_halted": halted,
        "open_position": bool(active),
        "trades": trades,
        "limitations": [
            "Current symbol filters throughout history; changes not reconstructed.",
            "Assumed fills: real FOK entries may expire or be rejected.",
            "Fees assumed 0.1%; current account rates used only in real engine.",
            "Stop slippage 0.05% assumed; market gaps can be worse.",
            "Residual BTC marked to close, including amounts too small to sell.",
            "Not evidence of future performance; no optimization or verified live record.",
        ],
    }


def main():
    candles = bot.load_candles(bot.ROOT / "data" / "BTCUSDT-1h.csv")
    rules = json.loads((bot.ROOT / "data" / "exchange_rules.json").read_text())
    info = {
        "status": rules["status"],
        "filters": list(rules["filters"].values()),
        "ocoAllowed": True,
        "otoAllowed": True,
        "orderTypes": ["STOP_LOSS"],
    }
    result = run(candles, info)
    (bot.ROOT / "data" / "live_backtest.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
