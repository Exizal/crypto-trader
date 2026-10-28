# Security

## Scope

This application runs under the current Windows user and assumes that user, the operating system and the installed Python/runtime are trusted. It does not protect credentials from malware or another program running with the same Windows identity. It does not attempt to defeat a malicious owner editing the program or maintaining another account client.

Do not post vulnerabilities containing API keys or account data in public issues. Revoke exposed keys through the provider and inspect the exchange directly. A reproducible report can use fabricated credentials and mocked responses, as the tests do.

## Implemented controls

- **Credential storage:** Binance and OpenAI connection records use Windows DPAPI encryption. They are separate files in `.private/`, excluded from source control and distribution.
- **Transport:** authenticated requests use fixed HTTPS hosts, certificate verification, no redirects and bounded JSON responses. Errors do not print credentials, signed request URLs or raw account/model payloads. Binance rate-limit backoff is honored.
- **Restricted exchange access:** the trading transport allows account/order reads and the single protected BTCUSDT entry-list operation. Withdrawals, transfers, leverage, standalone buys and blanket order cancellation are not implemented. Permissions are checked before enabling the engine and periodically while running.
- **Account isolation:** the ledger tracks a fixed 10 USDT starting allocation and reserves pre-existing Bitcoin. Both the API-key mutex used by the earlier version and a verified account-identity mutex are acquired, reducing concurrent spending across copies and API keys. Other independent trading programs are outside these locks.
- **Persistent records:** ledger writes are atomic and authenticated with a purpose-derived key. Valid legacy records are verified before migration. Initialized connections cannot silently allocate a new budget when their ledger is missing. Recent Binance order history and all open orders are checked for untracked application orders.
- **Order uncertainty:** stable IDs and intent are saved before submission. A timeout, failed response or restart triggers status reconciliation, not automatic resubmission. Fill quantities must reconcile before accounting proceeds; trade IDs prevent double counting.
- **AI isolation:** only an explicit allowlist of numeric market/proposal fields is sent. The model has no tools, account identifiers or Binance credentials. Its response is strictly validated and can only veto an entry. A recent approval must match the exact unchanged plan and signal before submission. Unavailable, refused, malformed or stale AI responses do not authorize orders.
- **AI usage:** attempts are persisted before a potentially billable request. Six attempts per UTC day and 512 output tokens per request are enforced locally. A changed quote does not cause a failed signal review to be retried after restart. Set a provider project hard spend limit; local request limits are not an organization-wide billing guarantee.
- **Publication:** `.gitignore` excludes credentials, ledgers, backups, logs, downloaded data and binaries. A tracked-file checker rejects forbidden paths, unexpected binary files and common credential patterns. The Windows CI job has read-only repository permissions and uses commit-pinned actions without persisted Git credentials.

## Review coverage

The local review combined manual tracing, regression tests, Ruff and Bandit. Regression cases cover host/redirect rejection, response limits, secret-free AI payloads, strict response parsing, AI request persistence and quotas, approval binding, ledger integrity, stale/untracked orders, fill reconciliation, lost state and the absence of unauthorized exchange endpoints.

Bandit suppressions are limited to reviewed subprocess sites: importing `subprocess`, launching a fixed current-executable worker from an action allowlist without a shell, terminating that owned worker with the absolute Windows system `taskkill.exe`, and a fixed Git read in the publication checker. These annotations do not suppress SSL, credential, general shell-injection or network checks.

This is a local engineering review, not an independent penetration test or security certification. Signed Binance execution and paid OpenAI generation have not been exercised with real credentials. No tests assert that future returns are positive.

## Remaining limitations

- Windows sign-in encryption does not protect against the same user or an administrator running malicious code. Python strings are not guaranteed to be zeroed from process memory.
- Ledger authentication detects modification, but is not an external append-only audit log. Recent-order verification checks the latest 1,000 BTCUSDT orders plus all open orders; do not manually restore old state or delete records. Account/API-key migration requires deliberate reconciliation.
- Exchange-hosted targets and stops reduce reliance on the local process but can be rejected, delayed, activated unsuccessfully or filled at worse prices. Small residual balances may be too small to protect or sell. Planned loss limits are not actual maximum-loss guarantees.
- Binance and OpenAI outages, model-access restrictions, manual account activity and provider rule changes can interrupt automation. A conservative halt may require reviewing the account outside the app; there is no override that erases a live budget or an uncertain order.
- Historical research excludes AI reviews and assumes fills. It cannot establish the effectiveness of the model filter. AI outputs may be mistaken and do not establish investment suitability or profitability.
- The EXE is unsigned. A release is not deployed as a background service, and a computer that is off cannot submit or reconcile new entries. Existing exchange orders may remain active.
