# Kallisto V1.1 five-session review: October 26–30, 2026

The GitHub dashboard diagnostic was **FRESH** (checked 2026-10-30 20:49 ET), with Azure last cycle 16:05 ET and expected latest completed NYSE session 2026-10-30. Five complete V1.1 sessions were verified in the daily performance log, from October 26 through October 30.

**Primary accounting:** fee-adjusted daily net P/L is the sum of gross realized trade P/L minus modeled Moomoo AU round-trip fees from the existing `scalping_fees.py` model. Daily net return divides that amount by the preceding day's fee-adjusted equity. V1.1 begins after the October 23 net equity of approximately $794.28; historical V1.0 fees are not charged to V1.1 again.

| NYSE date | Trades | Gross P/L USD | Fees USD | Net P/L USD | Net return |
|---|---:|---:|---:|---:|---:|
| Oct 26 | 8 | -6.65 | 16.39 | -23.04 | -2.90% |
| Oct 27 | 8 | +2.17 | 15.98 | -13.81 | -1.79% |
| Oct 28 | 7 | +2.57 | 14.01 | -11.45 | -1.51% |
| Oct 29 | 6 | -9.99 | 21.39 | -31.39 | -4.21% |
| Oct 30 | 3 | -17.14 | 19.93 | -37.07 | -5.19% |
| **Total** | **32** | **-29.04** | **87.71** | **-116.75** | **-14.70% compounded** |

**Required evaluation:** average net daily return **-3.12%**; median **-2.90%**; days at or above +1.0% net **0/5 (0%)**; total net P/L **-$116.75**; modeled fees **410.9% of the $21.35 sum of positive gross trade profits** (not divided by the negative signed gross P/L); trades per day **6.4**; net profit factor **0.0495**; maximum net daily loss **-$37.07 (-5.19%)** on October 30; V1.1-only maximum fee-adjusted daily-close drawdown **14.70%**, from $794.28 to $677.53. The full-experiment drawdown is separately about 29.78%; the two periods must not be conflated.

## Forward-only V1.2 decision

Five sessions are a small sample, but the combination of 0/5 net-target days, a net loss and heavy fees materially misses the stated research objective. V1.2 therefore begins **no earlier than the next NYSE session, November 2, 2026**. No V1.1 trade, equity or audit log is rewritten.

V1.2 restricts entries to **Titan securities**, at most **2 distinct trades per day** and **1 simultaneous position**. Minimum confidence is **0.72**, risk per trade **0.5% of fee-adjusted equity**, open risk **1%**, gross exposure **50%**, position cap **45%**, cash reserve **30%**, reward/risk floor **2.0**, minimum Titan target **2%**, maximum hold **60 minutes**. Entry requires expected gross target profit at least **3x modeled round-trip fees**, expected net target profit at least **0.5% of fee-adjusted equity**, and expected net target profit at least **1.25x modeled stop risk**. A zero-trade day is valid.

Once realized net P/L reaches **+1% of starting fee-adjusted daily equity**, new entries stop. They also stop at **-1.5% fee-adjusted daily mark-to-market return** or a **10% forward V1.2 net-equity drawdown**. The original **2% gross daily breaker**, **10% gross portfolio drawdown pause**, no leverage, no options and forced same-day liquidation remain. The V1.2 net drawdown risk anchor is new and forward-looking, not a reset of historical reported losses.

The Azure Blob configuration is the runtime source of truth; a one-time migration upgrades persisted V1.1 state on/after November 2 only if five completed V1.1 daily rows exist. A GitHub commit alone does not prove Azure deployment succeeded. This is simulation-only; no live-money trading is enabled. No daily return is guaranteed. Reassess with out-of-sample V1.2 sessions and acknowledge synthetic fill, slippage, market-data and unknown security-specific fee limitations.
