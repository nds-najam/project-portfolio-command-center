import pandas as pd
import streamlit as st

from src import calculations as calc, charts, ui
from src.config import AS_OF, SEVERITIES, SEVERITY_COLORS


def render(ctx):
    d = ctx["data"]
    p, iss = d["projects"], d["issues"]
    ui.section("Issues & risks")
    if p.empty:
        return ui.no_data()
    op = calc.open_items(iss)
    if op.empty:
        return st.info("No open issues or risks for the current selection.", icon="ℹ️")
    op = op.merge(p[["project_id", "project_name", "client", "region", "project_manager"]], on="project_id", how="left")
    overdue = op[op.due_date < pd.Timestamp(AS_OF)]
    issues_only = op[op.item_type == "Issue"]
    ui.kpi_cards([
        ("Open Issues", f"{len(issues_only)}", "", ""),
        ("Critical Issues", f"{int((issues_only.severity == 'Critical').sum())}", "open", "red"),
        ("Overdue Issues", f"{int((overdue.item_type == 'Issue').sum())}", "past due date", "amber"),
        ("Open Risks", f"{int((op.item_type == 'Risk').sum())}", "", ""),
    ])
    st.caption("Charts include open issues and open risks.")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Open items by severity")
        ui.show(charts.count_bar(op, "severity", SEVERITY_COLORS, order=SEVERITIES), "is_sev")
        st.caption("Open items by client")
        ui.show(charts.count_bar(op, "client"), "is_client")
    with c2:
        st.caption("Open items by category")
        ui.show(charts.count_bar(op, "category"), "is_cat")
        st.caption("Open items by region")
        ui.show(charts.count_bar(op, "region"), "is_region")

    ui.section("Overdue issues requiring attention")
    if overdue.empty:
        return st.success("No overdue items.")
    sev_rank = {s: i for i, s in enumerate(SEVERITIES)}
    t = overdue.assign(rank=overdue.severity.map(sev_rank), days_overdue=(pd.Timestamp(AS_OF) - overdue.due_date).dt.days)
    t = t.sort_values(["rank", "days_overdue"], ascending=[True, False])
    t = t.rename(columns={"project_id": "Project", "item_type": "Type", "issue": "Issue", "category": "Category",
                          "severity": "Severity", "owner": "Owner", "due_date": "Due Date", "days_overdue": "Days Overdue",
                          "status": "Status", "client": "Client", "region": "Region"})
    st.dataframe(ui.style_table(t[["Project", "Client", "Region", "Type", "Issue", "Category", "Severity", "Owner", "Due Date", "Days Overdue", "Status"]],
                                severity=["Severity"]),
                 hide_index=True, width="stretch", height=min(60 + 35 * len(t), 520),
                 column_config={"Due Date": st.column_config.DateColumn(format="DD MMM YYYY")})
