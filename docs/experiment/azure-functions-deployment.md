# Azure Functions Deployment - Kallisto V1

Kallisto V1 uses Azure Functions as the trading clock instead of GitHub Actions cron. GitHub remains the source repository and CI/test/deployment source. Azure Blob Storage is the persistent source of truth for the running experiment.

## Runtime design

```text
Azure timer around U.S. market hours
        ->
cheap New York-time guard
        ->
restore Kallisto state from Azure Blob Storage
        ->
run one guarded scalping cycle
        ->
NYSE calendar/time guard
        ->
monitor positions / call GPT when decision is due
        ->
persist state + reports back to Blob Storage
        ->
function exits
```

The active timer uses a broad UTC window that safely covers New York market hours across daylight-saving changes. A cheap New York-time guard runs before Blob Storage sync, and the Python strategy still performs the final NYSE calendar/time validation.

The old GitHub market scheduler is manual-only so it cannot create a second trading clock.

## Current Azure resources

The deployed research environment uses:

- resource group `rg-llm-scalper-v1`
- Function App `ken-llm-scalper-v1`
- Linux / Python 3.12
- Flex Consumption plan
- Standard LRS storage
- Azure Blob Storage for persistent Kallisto state

The Azure resource names are intentionally left unchanged even though the product/research-platform name is now **Kallisto**. Renaming Azure resources is not required for the brand change and could create unnecessary deployment risk.

The Blob container `scalping-v1-state` is created automatically by Kallisto on the first successful in-window invocation.

## Function App application settings

Required settings include:

- `OPENAI_API_KEY` = OpenAI API key; never commit it to GitHub
- `SCALPING_STATE_CONTAINER` = `scalping-v1-state`
- `FUNCTIONS_WORKER_RUNTIME` = `python`

`AzureWebJobsStorage` is configured by Azure and is reused by Kallisto for experiment state unless another storage-setting name is explicitly configured.

## GitHub deployment authentication

Kallisto uses **OIDC / Azure RBAC** for GitHub Actions deployment. The previous publish-profile deployment path is no longer required.

The repository keeps the Azure Function App name in the GitHub Actions variable:

- `AZURE_FUNCTIONAPP_NAME`

The deployment workflow uses the Azure-created OIDC client, tenant and subscription secret references. Do not expose the underlying secret values.

## Deploy

1. Open GitHub -> Actions.
2. Select `Deploy Kallisto V1 to Azure Functions`.
3. Select `Run workflow` on branch `main`.
4. Wait for compile checks, deterministic smoke tests, OIDC login, and Azure deployment to finish successfully.

The workflow remains manual so code changes do not automatically replace the production research runtime without an explicit deploy action.

## Verify before counting Day 1

In Azure Portal -> Function App -> Functions, confirm `scalping_timer` exists.

In Monitor / Log stream, confirm timer invocations execute successfully during the eligible weekday market window.

For the first real NYSE session, verify Blob Storage contains Kallisto state such as:

```text
scalping-v1-state/
  state/portfolio_state.json
  state/decision_log.jsonl
  state/trade_log.csv
  state/daily_performance.csv
  state/api_costs.csv
  state/adaptive_config.json
  state/weekly_evaluations.jsonl
  state/improvement_metrics.csv
  state/strategy_versions.csv
  state/baseline_replay.csv
  reports/results/...
```

A valid Day 1 requires actual Kallisto market-cycle evidence. A zero-trade day can be legitimate only if decision logging proves the LLM evaluated eligible setups. A day with no decision records because the runtime failed does not count.

## Cost controls

Kallisto is designed for short timer-triggered invocations and a small Blob Storage footprint. Azure usage should be monitored rather than assumed to be exactly $0. Application Insights, storage transactions, and accidental resource configuration can still create charges. OpenAI API usage is billed separately.

## Moomoo transferability

The Azure Function is currently a simulation orchestration layer. A future Moomoo Australia deployment must preserve Kallisto's deterministic risk manager and add production-grade broker reconciliation, data freshness checks, execution-state validation, order idempotency, short eligibility, partial-fill handling, and verified end-of-day flat status.
