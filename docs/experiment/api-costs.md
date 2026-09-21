# API Cost Tracking

Every OpenAI call records:

- run date
- portfolio
- run type
- model
- input tokens
- output tokens
- total tokens
- estimated input cost
- estimated output cost
- estimated total cost
- cumulative cost

The cost log is stored at:

`user_side/personal_experiment/cost_tracking/api_cost_log.csv`

The experiment also includes session guards so duplicate or holiday runs stop before an API call is made.
