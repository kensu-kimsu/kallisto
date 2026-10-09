# Azure Functions deployment - Final V1

Final V1 now uses Azure Functions as the trading clock instead of GitHub Actions cron. GitHub remains the source repository and CI/test/deployment source. Azure Blob Storage is the persistent source of truth for the running experiment.

## Runtime design

```text
Azure timer trigger (every 5 minutes on weekdays)
        ->
restore Final V1 state from Azure Blob Storage
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

The Python strategy still decides whether the invocation is inside the NYSE experiment window. This makes daylight-saving changes safe because the Function does not hard-code New York market hours in UTC.

The old GitHub market scheduler is manual-only so it cannot create a second trading clock.

## Azure resources to create

Create these in the same resource group and region when possible:

1. Resource group, for example `rg-llm-scalper-v1`.
2. Storage account using Standard / LRS. Azure Functions needs it and Final V1 also stores its state there.
3. Linux Function App running Python 3.12 on a Consumption/Flex Consumption plan.
4. Application Insights is optional. Disable or limit retention if you want the lowest possible cost.

The Blob container `scalping-v1-state` is created automatically by the code on first successful invocation.

## Function App application settings

Set these in Azure Portal -> Function App -> Settings -> Environment variables / Configuration:

- `OPENAI_API_KEY` = your OpenAI API key. Never commit it to GitHub.
- `SCALPING_STATE_CONTAINER` = `scalping-v1-state`
- `FUNCTIONS_WORKER_RUNTIME` = `python`

`AzureWebJobsStorage` is normally created/configured automatically with the Function App. Final V1 reuses that connection for experiment state unless you explicitly set `SCALPING_STORAGE_CONNECTION_SETTING` to another application-setting name.

## GitHub deployment settings

In the GitHub repository:

Settings -> Secrets and variables -> Actions -> Variables:

- create variable `AZURE_FUNCTIONAPP_NAME` with the exact Azure Function App name.

Settings -> Secrets and variables -> Actions -> Secrets:

- create secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` containing the Function App publish profile downloaded from Azure Portal.

Do not paste the publish profile into source files or chat messages.

## Deploy

After the Azure resources and GitHub values exist:

1. Open GitHub -> Actions.
2. Select `Deploy Final V1 to Azure Functions`.
3. Select `Run workflow` on branch `main`.
4. Wait for tests and deployment to finish successfully.

The deployment workflow is intentionally manual until the Azure account is configured so an incomplete Azure setup cannot cause repeated failed deploys.

## Verify before counting Day 1

In Azure Portal -> Function App -> Functions, confirm `scalping_timer` exists.

In Monitor / Log stream, confirm a timer invocation occurs on a weekday. Outside the NYSE trading window it should exit normally without trading.

For the first real NYSE session, verify after 09:40 ET that Blob Storage contains:

```text
scalping-v1-state/
  state/portfolio_state.json
  state/decision_log.jsonl
  state/trade_log.csv
  state/daily_performance.csv
  state/api_costs.csv
```

A valid Day 1 requires at least one completed trading-cycle record. A zero-trade day can be legitimate only if decision logging proves the LLM evaluated the market and chose/rejected setups. A day with no decision log is an infrastructure failure and should not count.

## Cost controls

Create an Azure Cost Management budget for the subscription/resource group. Suggested warning thresholds are A$1, A$2 and A$5 per month. Final V1 is designed for short timer-triggered invocations and should normally remain within Azure Functions' free/very-low-cost usage range, but storage, logging and accidental resource configuration can still create charges.

## Moomoo transferability

The Azure Function is an orchestration layer only. When moving to Moomoo Australia, keep the same timer/strategy/risk flow and replace the public market-data + simulated execution adapters with Moomoo-backed adapters. See `docs/experiment/moomoo-live-transfer.md`.
