import streamlit as st

from src import calculations as calc, ui
from src.data_generator import SCENARIOS

SCENARIO_HELP = {
    "Normal Portfolio": "Balanced portfolio: a minority of projects slip or overrun.",
    "Schedule Delay": "Most projects run behind plan, with longer delays and more open issues.",
    "Cost Overrun": "Many projects are forecast above budget, with larger overruns.",
    "High Risk Portfolio": "Combined delays, overruns, high risk ratings and a large issue backlog.",
}


def render(ctx):
    full = ctx["full"]
    ui.section("Demo controls")
    st.markdown("All data in this POC is **synthetic**. Pick a scenario to reshape the portfolio, or generate a new random dataset.")
    names = list(SCENARIOS)
    c1, c2 = st.columns([2, 1])
    with c1:
        choice = st.radio("Scenario", names, index=names.index(st.session_state["scenario"]),
                          captions=[SCENARIO_HELP[n] for n in names])
        if choice != st.session_state["scenario"]:
            st.session_state["scenario"] = choice
            st.session_state["reset_filters"] = True
            st.rerun()
    with c2:
        st.write("")
        st.write(f"Current seed: **{st.session_state['seed']}**")
        if st.button("Generate new demo dataset", type="primary"):
            st.session_state["seed"] = int(st.session_state["seed"]) + 1
            st.session_state["reset_filters"] = True
            st.rerun()
        if st.button("Restore default dataset"):
            st.session_state["seed"] = 42
            st.session_state["reset_filters"] = True
            st.rerun()

    ui.section("Health score method")
    cfg = calc.HEALTH_CONFIG
    z = cfg["zero_at"]
    st.markdown(f"""
The **health score (0-100)** is a transparent weighted average of five component scores. Each component is 100 when there
is no problem and falls linearly to 0 at the stated limit. All values live in `HEALTH_CONFIG` (`src/calculations.py`) and the
scoring functions can be swapped for real business rules or a model.

| Component | Weight | 100 when | 0 when |
|---|---|---|---|
| Schedule | {cfg['weights']['schedule']:.0%} | on / ahead of plan | ≥ {z['schedule_days_late']} days behind |
| Cost | {cfg['weights']['cost']:.0%} | forecast ≤ budget | forecast ≥ {z['cost_overrun_pct']:.0%} over budget |
| Progress | {cfg['weights']['progress']:.0%} | actual ≥ planned completion | ≥ {z['progress_gap_pts']} pts behind planned |
| Open issues | {cfg['weights']['issues']:.0%} | none | ≥ {z['issue_points']} severity points (Critical 4, High 2, Medium 1, Low 0.5) |
| Risk level | {cfg['weights']['risk']:.0%} | Low = 100 | Medium = 60, High = 20 |

**Status bands:** ≥ {cfg['bands']['On Track']} **On Track** · {cfg['bands']['At Risk']}-{cfg['bands']['On Track'] - 1} **At Risk** · < {cfg['bands']['At Risk']} **Critical**.
Projects at 100% completion are shown as **Completed**. A project is counted as **Delayed** when it is more than
{calc.DELAY_THRESHOLD_DAYS} days behind schedule.

**Attention score** (prioritisation only, not a prediction): schedule delay 30 + cost overrun 25 + progress gap 20 +
open critical issues 15 + risk level 10 points.
""")

    ui.section("Data preview")
    tabs = st.tabs(["projects", "issues", "milestones", "financials"])
    for tab, key in zip(tabs, ["projects", "issues", "milestones", "financials"]):
        with tab:
            df = full.get(key)
            if df is None or df.empty:
                st.caption("_No data available._")
                continue
            st.caption(f"{len(df):,} rows × {df.shape[1]} columns (unfiltered)")
            st.dataframe(df, hide_index=True, width="stretch", height=300)
            st.download_button(f"Download {key}.csv", df.to_csv(index=False).encode("utf-8"), f"{key}.csv", "text/csv", key=f"dl_{key}")
