# User guide

## Connect and start

Open the EXE from a folder where you can save files. You do not need a separate Python installation. Choose English or Türkçe in the upper right.

**Connection** is for your Binance.com HMAC API key. An API key is a separate access pass, not your Binance password. Create it in Binance API Management with reading and Spot trading enabled, trusted-IP restrictions enabled, and withdrawals, transfers, margin and futures disabled. Binance may name the combined Spot permission “Spot & Margin”; this app implements only Spot operations. Complete login and verification on Binance yourself. Enter the key and secret in the app's masked fields and verify/save them.

**AI review** is for an OpenAI API key. The default model is `gpt-6-luna`. Read the sharing/billing notice and select the consent box before saving. The access check verifies the selected model is visible to your key; actual generation is requested only when a qualifying entry is proposed. OpenAI API charges are separate from the 10 USDT allocation. Set a project hard spend limit on the provider account.

On **Dashboard**, read the limits, select the real-order authorization box and click **Start automatic trading**. Have at least 10 USDT available in your Binance Spot wallet. The program does not move money into the account. It starts with real trading disabled on every launch.

## What happens automatically

Bitcoin is the asset being bought. USDT is the unit used to count the allocated balance. The program watches public prices and proposes a purchase when its fixed trend rule changes upward. It checks fees, available money, risk and Binance minimums, then asks OpenAI to review the proposal. A rejection or unavailable model means no purchase. Approval cannot override the fixed limits.

A qualifying purchase is submitted with a profit target and stop at Binance. The purchase must fill fully immediately or expire. On a full fill, Binance activates the exits. The app checks the exchange's actual order and fill records, rather than assuming success.

Keep the program open and the computer awake/online for new decisions and reconciliation. **Pause new purchases** and closing the app stop new decisions; a request already sent may finish. **Existing exchange exit orders can still execute while the app is paused or closed.** Inspect them in Binance if you need to manage them directly.

The starting budget is 10 USDT; exposure is capped at 7.50 USDT, including leftovers. Planned loss allowance per entry is 0.10 USDT; gaps, outages, rejected protection, fees and unsold Bitcoin may produce larger losses. Tiny residual BTC can be below the selling minimum and remain unprotected. Daily and overall loss checks stop new purchases; they cannot guarantee a maximum loss.

## Status and records

The dashboard shows the app's allocated money, its last-confirmed value, managed orders, last update and AI review status. It does not add your other Binance funds to the bot budget. A review score is not a probability of profit. Waiting for a signal or skipping a purchase can be normal, especially with a small balance.

If the app reports an uncertain order or asks you to check Binance, review the account directly. Do not delete `live_state.json` or `.private/` to reset it. Keep the entire folder; it contains the encrypted connections, budget ledger and local records. Keys and live state are never included in the GitHub repository.

The historical check is a rules-only comparison. It excludes AI, assumes fills and values remaining BTC at a recorded price, even when it is too small to sell alone. It is not a real trading record and does not prove profitability.

## Updating an existing installation

Pause new purchases and close the old version. Inspect any active exchange orders. Replace only the executable while keeping the existing `live_state.json`, `.private/`, settings and records together. Do not run a fresh second installation with the same account as a way to allocate another 10 USDT. The update verifies valid earlier ledgers before migrating their authentication format. It requires an OpenAI connection before new entries; existing Binance exits remain independent.

Account-key migration and recovery from missing/corrupt live records are not automated. Review [the security notes](../SECURITY.md) before attempting recovery. Signed order execution and paid AI generation still need validation with your eligible provider accounts. There is no demonstrated reliable profit.
