import streamlit as st

from src import calculations as calc, charts, insights, ui


def attention_dataframe(att):
    cols = ["Priority", "Project", "Client", "Region", "Progress", "Schedule Variance", "Budget Variance",
            "Risk", "Open Issues", "Recommended Attention", "Reason"]
    return ui.style_table(att[cols], risk=["Risk"], days=["Schedule Variance"], budget_var=["Budget Variance"],
                          formats={"Progress": "{:.0f}%", "Schedule Variance": "{:+.0f} d", "Budget Variance": "{:+.1f}%"})


def render(ctx):
    d = ctx["data"]
    p = d["projects"]
    if p.empty:
        return ui.no_data()
    k = calc.portfolio_kpis(p)
    att = calc.attention_table(p, d["issues"], top_n=10)

    ui.section("Portfolio overview")
    st.markdown(
        f"**{k['active']} active projects** · {calc.fmt_sar(k['contract_value'])} contract value · "
        f"{k['completion']:.0f}% overall completion · **{k['at_risk'] + k['critical']} at risk / critical** · "
        f"**{k['delayed']} delayed** · {calc.fmt_sar(k['exposure'])} forecast cost exposure")
    ui.kpi_cards([
        ("Total Projects", f"{k['total']}", f"{k['completed']} completed", ""),
        ("Active Projects", f"{k['active']}", "in delivery", ""),
        ("On Track", f"{k['on_track']}", "health score ≥ 80", "green"),
        ("At Risk", f"{k['at_risk']}", f"+ {k['critical']} critical (score < 60)", "amber"),
        ("Delayed Projects", f"{k['delayed']}", f"> {calc.DELAY_THRESHOLD_DAYS} days behind schedule", "red"),
        ("Total Contract Value", calc.fmt_sar(k["contract_value"]), f"Budget {calc.fmt_sar(k['budget'])}", ""),
        ("Budget Utilization", f"{k['utilization']:.0%}", f"{calc.fmt_sar(k['spent'])} spent of budget", ""),
        ("Overall Completion", f"{k['completion']:.0f}%", "contract-value weighted", ""),
    ], per_row=4)

    left, right = st.columns([1, 1])
    with left:
        ui.section("Management attention required")
        if att.empty:
            st.success("No projects currently exceed the attention threshold.")
        for r in att.head(3).itertuples():
            st.markdown(f'<div class="attn"><b>{r.Project}</b><br><span>{r.Reason}</span></div>', unsafe_allow_html=True)
    with right:
        ui.section("Management insights")
        ui.insight_box(insights.generate_insights(p, d["issues"], d["milestones"])[:6])

    ui.section("Portfolio health")
    c1, c2, c3 = st.columns([1, 1.3, 1.3])
    with c1:
        st.caption("Project health distribution")
        ui.show(charts.health_donut(p), "ex_donut")
    with c2:
        st.caption("Project status by client")
        ui.show(charts.status_stack(p, "client", horizontal=True), "ex_client")
    with c3:
        st.caption("Project status by region")
        ui.show(charts.status_stack(p, "region"), "ex_region")

    ui.section("Schedule and budget performance")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Planned vs actual completion % (active projects, largest gaps)")
        ui.show(charts.schedule_performance(p), "ex_sched")
    with c2:
        st.caption("Budget vs actual spend vs forecast cost, by client (SAR M)")
        ui.show(charts.budget_performance(p), "ex_budget")

    ui.section("Top projects requiring attention")
    if att.empty:
        st.caption("_No projects currently exceed the attention threshold._")
    else:
        with st.expander("How is the attention score calculated?"):
            st.markdown("Prioritisation only (not a prediction). Max 100 points: schedule delay 30 · forecast cost overrun 25 · "
                        "progress gap 20 · open critical issues 15 · risk level 10. Each factor scales linearly up to a cap "
                        "set in `ATTENTION_CONFIG` (`src/calculations.py`).")
        st.dataframe(attention_dataframe(att), hide_index=True, width="stretch",
                     height=min(40 + 35 * len(att), 420))
