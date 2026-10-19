# Kallisto Moomoo Paper Trading V1

Kallisto now has an **Azure-native Moomoo REST paper-trading shadow layer**. The original six-month simulation remains the primary experiment and is not replaced.

Real-money trading remains disabled by design. The Azure broker code only calls Moomoo's `/api/v1.0/sim-trade/...` endpoints.

## Architecture

```text
Azure Functions timer
        |
        v
Kallisto simulation cycle
        |
        +--> simulation state/logs
        |
        v
Moomoo paper shadow (optional)
        |
        v
Moomoo REST simulated-trading API
        |
        v
paper orders / broker positions
        |
        v
Azure Blob paper-shadow state + audit log
```

The user's PC does not need to remain online. OpenD is not required for this Azure path.

## Official Moomoo endpoints used

Base URL:

```text
https://webapi.moomoo.com
```

Paper-only endpoints used by Kallisto:

```text
GET  /api/v1.0/sim-trade/accounts
GET  /api/v1.0/sim-trade/{acc_id}/cash-info
GET  /api/v1.0/sim-trade/{acc_id}/positions
GET  /api/v1.0/sim-trade/{acc_id}/orders
GET  /api/v1.0/sim-trade/{acc_id}/max-buy-sell
POST /api/v1.0/sim-trade/{acc_id}/orders
POST /api/v1.0/sim-trade/{acc_id}/orders/{order_id}/cancel
```

Reference:
- https://open.moomoo.com/api/overview/getting-started
- https://open.moomoo.com/api/overview/api-reference

## Authentication

Kallisto uses Moomoo's **Traditional AppKey** mode for Azure because Moomoo documents it as suitable for server-side systems and backend jobs.

The request signature is built from:

```text
timestamp_ms
HTTP_METHOD
request_path
query_string
sha256(raw_body)
```

The code supports both:
- `ED25519`
- `RSA-SHA256`

The private key must never be committed to GitHub.

## Azure settings

Set these Function App application settings before enabling paper trading:

```text
KALLISTO_MOOMOO_PAPER_ENABLED=false
MOOMOO_APP_KEY=<your AppKey ID>
MOOMOO_PRIVATE_KEY_PEM=<private key PEM or Azure Key Vault reference>
MOOMOO_SIGN_ALGORITHM=ED25519
MOOMOO_PAPER_MARKET_ID=2
```

Optional:

```text
MOOMOO_PAPER_ACCOUNT_ID=<specific US simulated account ID>
MOOMOO_API_BASE_URL=https://webapi.moomoo.com
MOOMOO_HTTP_TIMEOUT_SECONDS=12
```

For security, use an **Azure Key Vault reference** for `MOOMOO_PRIVATE_KEY_PEM` rather than putting the private key directly into source control.

The Azure Functions platform resolves Key Vault references into the application setting, so the Python code still reads `MOOMOO_PRIVATE_KEY_PEM` normally.

## Safe activation sequence

Keep this setting first:

```text
KALLISTO_MOOMOO_PAPER_ENABLED=false
```

Then:

1. Create an AppKey in the Moomoo OpenAPI dashboard.
2. Generate the matching private/public key pair.
3. Upload only the public key to Moomoo.
4. Put the AppKey and private key into Azure settings / Key Vault.
5. Confirm the Function App deployment is healthy.
6. Turn on:
   ```text
   KALLISTO_MOOMOO_PAPER_ENABLED=true
   ```
7. On the first enabled invocation, Kallisto **arms paper mode without replaying old trades**.
8. Only LLM decisions created after that arming point may be mirrored to Moomoo paper trading.

## What the paper shadow does

For each new simulation decision after paper mode is armed:

- simulated closes are mirrored first as risk-reducing paper orders;
- new entries are checked by the deterministic broker safety gate;
- paper account equity is checked against the daily-loss breaker;
- stale decision timestamps are rejected;
- duplicate orders are prevented using deterministic event keys plus Moomoo order remarks;
- short entries query Moomoo's paper `max_sell_short_qty` before submission;
- broker positions, account equity and open orders are refreshed every cycle;
- all paper actions are logged separately from the simulation.

The Moomoo paper order remark has the form:

```text
Kallisto:<event-key>
```

Before submitting, Kallisto checks today's Moomoo paper orders for that exact remark. This gives a second idempotency barrier if Azure retries after a network interruption.

## Persistent Azure files

These are stored in the existing Blob state container:

```text
state/moomoo_shadow_state.json
state/moomoo_paper_log.jsonl
```

They do not overwrite:

```text
portfolio_state.json
trade_log.csv
daily_performance.csv
decision_log.jsonl
```

The simulation therefore remains independently auditable.

## Important behavior

Paper mode is a **shadow** of new Kallisto decisions, not a historical replay.

If paper mode is enabled today after many simulation sessions already exist, Kallisto records:

```text
PAPER_ARMED_NO_HISTORICAL_REPLAY
```

and begins mirroring only later decisions.

This prevents suddenly sending weeks of old trades into the paper account.

## Live-money protection

The Azure REST client rejects any request path outside:

```text
/api/v1.0/sim-trade/
```

The safety gate also rejects a `REAL` environment when live trading is disabled.

A future real-money adapter must be a separate, explicit implementation and should not reuse this paper client by simply changing a flag.

## What to compare

Once paper mode is running, keep both datasets:

```text
SIMULATION
- hypothetical fills
- original Kallisto six-month research track

MOOMOO PAPER
- broker-paper fills
- paper account equity
- paper positions
- paper order states
```

The purpose is to measure the execution gap before considering any live-money pilot.

## Promotion gates before live trading

Do not create a live branch until paper trading demonstrates a meaningful sample with:

- no duplicate orders
- no unexplained broker-state mismatches
- no stale-data entries
- correct short availability checks
- correct order cancellation behavior
- correct partial-fill/order-state handling
- no unintended overnight positions
- daily-loss lockout working
- stable Azure execution
- paper results reasonably consistent with the strategy's simulation behavior

A separate code review and explicit live-enable implementation should be required before any real-money capability is added.
