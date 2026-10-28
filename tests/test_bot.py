import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot
import connect_account


class StrategyTests(unittest.TestCase):
    def test_new_position_is_included_in_equity(self):
        candles = [bot.Candle(i * 3_600_000, 100, 101, 99, 100, 1) for i in range(55)]
        fast = [0.0] * 51 + [2.0] * 4
        slow = [1.0] * 55
        with patch.object(bot, "indicators", return_value=(fast, slow, [5.0] * 55)):
            report = bot.backtest(candles, 100, bot.Config(fee_rate=0, slippage=0))
        self.assertEqual(report["closed_trades"], 1)
        self.assertEqual(report["final_equity"], 100)
        self.assertEqual(report["max_drawdown_pct"], 0)

    def test_connector_cannot_call_order_endpoint(self):
        with patch("urllib.request.urlopen") as network:
            with self.assertRaises(ValueError):
                connect_account.signed_get("/api/v3/order", "fake-key", "fake-secret")
            network.assert_not_called()

    def test_paper_liquidates_on_loss_limit_instead_of_freezing_position(self):
        candles = [bot.Candle(i * 3_600_000, 100, 101, 99, 100, 1) for i in range(100)]
        state = bot.new_paper_state(100)
        state.update(cash=50, qty=0.5, entry=100, stop=70, peak=100)
        action = bot.paper_cycle(
            state, candles, 80, 81, {"status": "TRADING"}, bot.Config(), 100 * 3_600_000
        )
        self.assertEqual(action, "loss_limit")
        self.assertTrue(state["halted"])
        self.assertEqual(state["qty"], 0)
        self.assertLess(state["cash"], 90)

    def test_paper_rejects_stale_or_unclosed_candles(self):
        candles = [bot.Candle(i * 3_600_000, 100, 101, 99, 100, 1) for i in range(100)]
        for now in (99 * 3_600_000, 102 * 3_600_000):
            state = bot.new_paper_state(10)
            with self.assertRaises(RuntimeError):
                bot.paper_cycle(state, candles, 100, 101, {}, bot.Config(), now)
            self.assertEqual(state["cash"], 10)

    def test_ema_is_stable_for_flat_series(self):
        self.assertEqual(bot.ema([5.0] * 10, 3), [5.0] * 10)

    def test_position_size_obeys_risk_and_position_cap(self):
        cfg = bot.Config(risk_fraction=0.01, max_position_fraction=0.5)
        rules = {"step_size": 0.001, "min_qty": 0.001, "min_notional": 1}
        qty = bot.qty_for_entry(1000, 1000, 100, 10, rules, cfg)
        self.assertEqual(qty, 1.0)  # $10 risk and $500 notional cap

    def test_position_below_exchange_minimum_is_skipped(self):
        cfg = bot.Config(risk_fraction=0.01, max_position_fraction=0.5)
        rules = {"step_size": 0.001, "min_qty": 0.001, "min_notional": 5}
        self.assertEqual(bot.qty_for_entry(10, 10, 100, 20, rules, cfg), 0.0)

    def test_backtest_needs_warmup(self):
        candles = [bot.Candle(i * 3_600_000, 10, 11, 9, 10, 1) for i in range(20)]
        with self.assertRaises(ValueError):
            bot.backtest(candles)

    def test_fee_and_slippage_assumptions_are_reported(self):
        candles = [bot.Candle(i * 3_600_000, 100, 101, 99, 100, 1) for i in range(100)]
        report = bot.backtest(candles, 10, bot.Config(fee_rate=0.002, slippage=0.001))
        self.assertEqual(report["final_equity"], 10)
        self.assertEqual(report["assumptions"]["fee_rate"], 0.002)
        self.assertEqual(report["assumptions"]["slippage"], 0.001)


if __name__ == "__main__":
    unittest.main()
