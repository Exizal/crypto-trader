# Crypto Trader

Windows application for automated Binance.com Bitcoin spot trading with OpenAI entry reviews. The interface supports English and Turkish and stores API credentials using Windows sign-in encryption.

The program monitors the market continuously while it is open. A fixed strategy proposes entries; an AI review can accept or decline each qualifying proposal. Spending limits and exchange checks remain enforced by application code. Real trading starts disabled.

## Getting started

1. Open `Crypto Trader.exe` in a writable folder. Keep the whole folder together.
2. In **Connection**, save a Binance HMAC key with reading and Spot trading permissions, IP restrictions enabled, and withdrawals, transfers and leverage permissions disabled.
3. In **AI review**, save an OpenAI API key and model. The default is `gpt-6-luna`. Read the data-sharing and billing notice first. API charges are separate from the trading allocation; set an OpenAI project hard spend limit.
4. Return to **Dashboard**, review the authorization statement and click **Start automatic trading**. Available Binance Spot funds must include at least 10 USDT.

Never put API keys, passwords or verification codes in an issue, source file or chat. Enter keys only in the local application.

See the [English guide](docs/guide.en.md) or [Türkçe kullanım rehberi](docs/guide.tr.md) for setup, controls and upgrading.

## Trading behaviour

- BTCUSDT Spot only; no leverage, withdrawals or transfers.
- Fixed starting allocation: **10 USDT**. Maximum total exposure: **7.50 USDT**, including residual Bitcoin.
- Hourly 20/50 EMA upward crossover proposes an entry. OpenAI reviews a small numeric market snapshot and the proposed figures. It cannot modify an order or access Binance credentials.
- Planned entry loss allowance: **0.10 USDT** including estimated charges. This is not a guaranteed maximum loss.
- A successful purchase uses a Binance OTOCO list: fill-or-kill limit buy, followed on a full fill by a profit target and a market stop. The target is twice the planned stop distance; the stop is two ATRs below entry.
- At most three entry attempts per UTC day. New purchases pause after a 2% daily loss or a 10% fall from the highest bot value.
- Missing AI configuration, a declined/invalid review, API failure, stale information, accounting discrepancies or an uncertain order prevent new purchases. There is no fallback that bypasses AI approval.

**Pausing or closing the app stops new decisions. Existing Binance stop and target orders can remain active and sell.** Small Bitcoin remainders may be below the selling minimum and unprotected by an exit order. They remain included in the bot allocation and can lose value.

## AI and data

The OpenAI Responses API receives only public prices, indicators and proposed entry figures. Binance keys, account identifiers and the full portfolio are excluded. Responses must match a strict schema. The model has no tools or execution access. Its confidence score is an internal review threshold, not a probability of profit.

The application permits six review attempts per UTC day, with at most 512 output tokens per request, and persists attempts before sending them. Failed requests are not blindly repeated. These limits bound this app's request volume; provider billing and project spend limits are managed in the OpenAI account. Other API clients are outside these limits.

Historical checks evaluate the fixed rules **without AI**. They assume fills and use the downloaded exchange filters throughout the historical period. They do not validate the AI-assisted strategy or establish future profitability.

## Development

Runtime: Python 3.13 on 64-bit Windows 10/11, using the standard library. Development tools are pinned in `requirements-dev.txt`.

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m ruff check .
python -m bandit -r . -x ./tests,./work,./data,./.git -q
python trader_desktop.py
```

Download public research prices with `python bot.py fetch --days 365` and run `python backtest_live.py`. The downloaded `data/` directory is local and ignored by Git. Build the EXE with `./build-windows.ps1`; it embeds research data if a local `data/` directory exists, otherwise history can be downloaded from the app.

Before publishing, stage the intended source files and run `python scripts/check_repository.py`. The repository excludes `.private/`, account ledgers, logs, backups, downloaded data and compiled binaries. CI repeats tests, static checks and the publication file check without real credentials.

## Security and validation

See [SECURITY.md](SECURITY.md) for the threat model, controls and remaining limitations. Tests use fabricated keys and mocked account/model responses; Windows encryption is exercised with dummy data. No real exchange order or paid model generation was performed during development. Real account eligibility, the complete Binance order lifecycle and model access still require validation on the user's connection. Security checks reduce specific risks; they do not establish that the program is risk-free or profitable.

API-key migration, recovery from missing live records, automatic dust conversion, a Windows startup service and code signing are not implemented. Never reset or delete the live ledger to allocate another budget. This repository provides trading software, not a verified investment performance record.

## References

- [Binance Spot API](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Binance order filters](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md)
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits)
- [Windows data protection](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
