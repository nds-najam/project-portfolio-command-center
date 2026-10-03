import pandas as pd
import streamlit as st

from src import calculations as calc, charts, ui
from src.config import COLORS


def render(ctx):
    d = ctx["data"]
    p = d["projects"]
    ui.section("Project details")
    if p.empty:
        return ui.no_data()
    ids = p.sort_values("attention_score", ascending=False)["project_id"].tolist()
    names = dict(zip(p.project_id, p.project_name))
    if st.session_state.get("selected_project") not in ids:
        st.session_state["selected_project"] = ids[0]
    pid = st.selectbox("Select project", ids, key="selected_project", format_func=lambda i: f"{i} · {names[i]}")
    r = p[p.project_id == pid].iloc[0]

    col = COLORS[r.health_status]
    st.markdown(
        f"<h3 style='margin:6px 0 2px 0'>{r.project_name} "
        f"<span class='pill' style='background:{col}'>{r.health_status} · {r.health_score:.0f}</span></h3>"
        f"<div style='color:#6B7A90'>{r.project_id} &nbsp;|&nbsp; {r.client} &nbsp;|&nbsp; PM: {r.project_manager} "
        f"&nbsp;|&nbsp; {r.region} &nbsp;|&nbsp; {r.project_type}</div>", unsafe_allow_html=True)
    st.write("")
    sv = int(r.schedule_variance_days)
    over = r.budget_variance < 0
    ui.kpi_cards([
        ("Contract Value", calc.fmt_sar(r.contract_value), "", ""),
        ("Budget", calc.fmt_sar(r.budget), "", ""),
        ("Actual Spend", calc.fmt_sar(r.budget_spent), f"{r.budget_utilization:.0%} of budget", ""),
        ("Forecast Cost", calc.fmt_sar(r.forecast_cost),
         f"{'Over' if over else 'Under'} budget by {calc.fmt_sar(abs(r.budget_variance))}", "red" if over else "green"),
        ("Completion", f"{r.completion_percentage:.0f}%", f"planned {r.planned_completion_percentage:.0f}%", ""),
        ("Schedule Variance", f"{sv:+d} days" if sv else "0 days", "behind plan" if sv > 0 else "on / ahead of plan",
         "red" if sv > 14 else "amber" if sv > 7 else "green"),
        ("Open Issues", f"{r.number_of_open_issues}", f"{r.open_critical_issues} critical", "red" if r.open_critical_issues else ""),
        ("Open Risks", f"{r.number_of_open_risks}", f"Risk level: {r.risk_level}", ""),
    ], per_row=4)
    st.caption(f"Planned {r.planned_start:%d %b %Y} → {r.planned_end:%d %b %Y} · Forecast finish {r.forecast_end:%d %b %Y}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Progress", "Financials", "Milestones", "Issues & Risks", "Health breakdown"])
    fin = d["financials"][d["financials"].project_id == pid]
    with tab1:
        ui.show(charts.progress_line(fin, r), "pd_prog", "No progress history available for this project.")
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Budget vs actual spend vs forecast cost")
            ui.show(charts.project_cost_bars(r), "pd_cost_bars")
        with c2:
            st.caption("Cumulative spend")
            ui.show(charts.cost_curve(fin, r), "pd_cost_curve", "No financial history available for this project.")
    with tab3:
        m = d["milestones"][d["milestones"].project_id == pid]
        if m.empty:
            st.caption("_No milestone data for this project._")
        else:
            m = m.sort_values("planned_date").rename(columns={"milestone": "Milestone", "planned_date": "Planned Date",
                                                              "actual_forecast_date": "Actual / Forecast Date", "status": "Status"})
            st.dataframe(ui.style_table(m[["Milestone", "Planned Date", "Actual / Forecast Date", "Status"]], ms=["Status"]),
                         hide_index=True, width="stretch",
                         column_config={c: st.column_config.DateColumn(format="DD MMM YYYY") for c in ["Planned Date", "Actual / Forecast Date"]})
    with tab4:
        i = d["issues"][d["issues"].project_id == pid]
        if i.empty:
            st.caption("_No issues or risks logged for this project._")
        else:
            i = i.assign(is_open=~i.status.isin(calc.CLOSED)).sort_values(["is_open", "due_date"], ascending=[False, True])
            i = i.rename(columns={"item_type": "Type", "issue": "Issue", "category": "Category", "severity": "Severity",
                                  "owner": "Owner", "due_date": "Due Date", "status": "Status"})
            st.dataframe(ui.style_table(i[["Type", "Issue", "Category", "Severity", "Owner", "Due Date", "Status"]], severity=["Severity"]),
                         hide_index=True, width="stretch",
                         column_config={"Due Date": st.column_config.DateColumn(format="DD MMM YYYY")})
    with tab5:
        w = calc.HEALTH_CONFIG["weights"]
        b = pd.DataFrame([(n.title(), r[f"score_{n}"], w[n] * 100, r[f"score_{n}"] * w[n]) for n in w],
                         columns=["Component", "Score (0-100)", "Weight %", "Contribution"])
        st.dataframe(b, hide_index=True, width="stretch",
                     column_config={"Score (0-100)": st.column_config.NumberColumn(format="%.0f"),
                                    "Weight %": st.column_config.NumberColumn(format="%.0f"),
                                    "Contribution": st.column_config.NumberColumn(format="%.1f")})
        st.caption(f"Health score = sum of contributions = **{r.health_score:.1f}** → {r.health_status}")
