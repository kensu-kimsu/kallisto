"""Sanitized V1.4 reporting. Missing first session is an expected pending state."""
from __future__ import annotations
import html
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas_market_calendars as mcal
from azure.core.exceptions import ResourceNotFoundError

def render(container, results: Path, readme: Path, v12_daily: list[dict]) -> None:
    def load(prefix, name):
        try:
            raw = container.get_blob_client(prefix + "/" + name).download_blob().readall()
        except ResourceNotFoundError:
            return []
        return [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
    sessions = sorted({r["date"]: r for r in load("v14", "sessions.jsonl")
                       if r.get("version") == "V1.4" and r.get("completed") is True}.values(),
                      key=lambda r:r["date"])
    trades = [t for t in load("v14", "trades.jsonl") if t.get("date") in {r["date"] for r in sessions}]
    decisions = load("v14", "decisions.jsonl")
    v13 = {r["date"]:r for r in load("v13", "sessions.jsonl")
           if r.get("completed") is True and r.get("version") == "V1.3"}
    today = datetime.now(ZoneInfo("America/New_York"))
    cal = mcal.get_calendar("NYSE")
    sched = cal.schedule(start_date=today.date()-timedelta(days=15), end_date=today.date())
    expected = [str(d.date()) for d,row in sched.iterrows()
                if row["market_close"].to_pydatetime()+timedelta(minutes=20) <= today]
    latest_expected = expected[-1] if expected else None
    first = sessions[0]["date"] if sessions else None
    start = float(sessions[0]["starting_equity"]) if sessions else 5000.0
    end = float(sessions[-1]["ending_equity"]) if sessions else start
    peak, dd = start, 0.0
    for r in sessions:
        equity = float(r["ending_equity"])
        peak = max(peak, equity)
        dd = max(dd, 100*(peak-equity)/peak if peak else 0)
    reasons = Counter(t.get("reason","UNKNOWN") for t in trades)
    rejections = Counter(x.get("reason","UNKNOWN") for d in decisions
                         for key in ("execution_rejections","reachability_rejections","screening_rejections")
                         for x in d.get(key,[]))
    statuses = Counter(d.get("status","UNKNOWN") for d in decisions)
    matched = [r for r in sessions if r["date"] in v13]
    matched_dates = {r["date"] for r in matched}
    v14_matched_trades = [t for t in trades if t["date"] in matched_dates]
    v13_matched_trades = [t for t in load("v13","trades.jsonl") if t.get("date") in matched_dates]
    # Compare identical completed dates using returns, not absolute account dollars.
    v14_base = float(matched[0]["starting_equity"]) if matched else None
    v13_base = float(v13[matched[0]["date"]]["starting_equity"]) if matched else None
    v14_ret = 100*sum(float(t["net_pnl"]) for t in v14_matched_trades)/v14_base if v14_base else None
    v13_ret = 100*sum(float(t["net_pnl"]) for t in v13_matched_trades)/v13_base if v13_base else None
    daily = {r["date"]:r for r in v12_daily}
    prior = [r for r in v12_daily if first and r["date"] < first]
    benchmark = {}
    if matched and prior:
        for key,label in (("sp500_normalized","sp500"),("nasdaq100_normalized","nasdaq100")):
            if all(r["date"] in daily and daily[r["date"]].get(key) for r in matched):
                base=float(prior[-1].get(key) or 0)
                if base:
                    benchmark[label+"_matched_return_pct"] = 100*(float(daily[matched[-1]["date"]][key])/base-1)
    summary = {
        "version":"V1.4", "status":"ACTIVE" if sessions else "AWAITING_FIRST_COMPLETED_SESSION",
        "completed_sessions":len(sessions), "first_date":first,
        "last_date":sessions[-1]["date"] if sessions else None,
        "expected_latest_session":latest_expected,
        "freshness":("FRESH" if sessions[-1]["date"] == latest_expected else "STALE") if sessions else "PENDING",
        "starting_equity":start, "ending_equity":end, "net_pnl":end-start,
        "net_return_pct":100*(end/start-1), "gross_pnl":sum(float(t["gross_pnl"]) for t in trades),
        "fees":sum(float(t["fees"]) for t in trades),
        "trades":len(trades), "wins":sum(float(t["net_pnl"])>0 for t in trades),
        "win_rate_pct":100*sum(float(t["net_pnl"])>0 for t in trades)/len(trades) if trades else None,
        "session_end_drawdown_pct":dd,
        "sampled_intraday_risk":[r["sampled_risk"] for r in sessions if r.get("sampled_risk")],
        "no_trade_dates":[r["date"] for r in sessions if r["date"] not in {t["date"] for t in trades}],
        "exit_reasons":dict(reasons), "decision_statuses":dict(statuses),
        "rejection_reasons":dict(rejections),
        "matched_v13_dates":sorted(matched_dates),
        "matched_v14_net_return_pct":v14_ret, "matched_v13_net_return_pct":v13_ret,
        "matched_v14_trades":len(v14_matched_trades), "matched_v13_trades":len(v13_matched_trades),
        **benchmark,
    }
    results.mkdir(parents=True, exist_ok=True)
    (results/"v14_summary.json").write_text(json.dumps(summary,indent=2)+"\\n")
    (results/"v14_sessions.jsonl").write_text("".join(json.dumps({
        k:r.get(k) for k in ("date","version","starting_equity","ending_equity","completed")})+"\\n"
        for r in sessions))
    # Only selected numeric and non-sensitive entry evidence is published; raw AI output stays in Azure.
    allow = ("date","ticker","side","entry_time","exit_time","entry_price","exit_price",
             "shares","stop_price","target_price","confidence","gross_pnl","fees","net_pnl","reason")
    (results/"v14_trades.jsonl").write_text("".join(json.dumps({k:t[k] for k in allow if k in t})+"\\n" for t in trades))
    block = "\\n".join([
        "<!-- V14_REPORT_START -->",
        "## Kallisto V1.4 — independent research experiment",
        "",
        "> **Simulation only.** V1.4 starts with a separate $5,000 virtual account; V1.3 remains the unchanged control. No historical V1.3 trades are copied into V1.4.",
        "",
        "| Metric | V1.4 |","|---|---:|",
        f"| Status | {summary['status']} |",
        f"| Completed NYSE sessions | {len(sessions)} |",
        f"| Starting capital | ${start:,.2f} |",
        f"| Ending capital | ${end:,.2f} |",
        f"| Net P/L after modeled fees | ${end-start:,.2f} |",
        f"| Net return | {summary['net_return_pct']:.2f}% |",
        f"| Gross P/L | ${summary['gross_pnl']:,.2f} |",
        f"| Modeled fees | ${summary['fees']:,.2f} |",
        f"| Closed trades | {len(trades)} |",
        f"| Win rate | {summary['win_rate_pct']:.2f}% |" if trades else "| Win rate | N/A — no closed trades |",
        f"| Session-end drawdown | {dd:.2f}% |",
        f"| No-trade sessions | {', '.join(summary['no_trade_dates']) or 'None'} |",
        f"| Freshness | {summary['freshness']} |",
        f"| V1.3 matched-session net return | {v13_ret:.2f}% |" if v13_ret is not None else "| V1.3 matched-session net return | Pending matched sessions |",
        f"| V1.4 matched-session net return | {v14_ret:.2f}% |" if v14_ret is not None else "| V1.4 matched-session net return | Pending matched sessions |",
        f"| Matched NYSE sessions | {len(matched)} |",
        "",
        "[Detailed V1.4 metrics, stop reasons, AI decision rejections, benchmarks and sampled drawdown](docs/results/v14_summary.json)",
        "",
        "[V1.4 completed sessions](docs/results/v14_sessions.jsonl) · [V1.4 trades](docs/results/v14_trades.jsonl)",
        "",
        "Comparisons use identical completed dates, modeled fees and percentage returns. Missing benchmark data is shown as unavailable, not invented.",
        "<!-- V14_REPORT_END -->"])
    content = readme.read_text()
    a,b = "<!-- V14_REPORT_START -->","<!-- V14_REPORT_END -->"
    if a in content and b in content:
        content = content[:content.index(a)] + block + content[content.index(b)+len(b):]
    else:
        content += "\\n\\n"+block+"\\n"
    readme.write_text(content)
