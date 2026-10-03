import streamlit as st

from src import ui


def open_project(pid):
    st.session_state["selected_project"] = pid
    st.session_state["nav"] = "Project Details"


def render(ctx):
    p = ctx["data"]["projects"]
    ui.section("Project portfolio")
    if p.empty:
        return ui.no_data()
    st.caption(f"{len(p)} projects match the filters, ordered by management attention. Click a row to select a project, "
               "then open its details. Sort by any column header.")
    t = p.sort_values("attention_score", ascending=False)
    view = t.rename(columns={
        "project_id": "Project ID", "project_name": "Project Name", "client": "Client", "region": "Region",
        "project_manager": "Manager", "completion_percentage": "Completion", "schedule_variance_days": "Schedule Variance",
        "risk_level": "Risk", "health_status": "Health", "health_score": "Health Score"})
    view["Budget Utilization"] = t["budget_utilization"].values * 100
    cols = ["Project ID", "Project Name", "Client", "Region", "Manager", "Completion", "Schedule Variance",
            "Budget Utilization", "Risk", "Health", "Health Score"]
    view = view[cols].reset_index(drop=True)
    styled = ui.style_table(view, health=["Health"], risk=["Risk"], days=["Schedule Variance"],
                            formats={"Schedule Variance": "{:+.0f} d", "Budget Utilization": "{:.0f}%", "Health Score": "{:.0f}"})
    ev = st.dataframe(styled, hide_index=True, width="stretch", height=560, on_select="rerun",
                      selection_mode="single-row", key="portfolio_table",
                      column_config={"Completion": st.column_config.ProgressColumn("Completion", min_value=0, max_value=100, format="%.0f%%")})
    rows = ev.selection.rows if ev and ev.selection else []
    if rows and rows[0] < len(view):
        r = view.iloc[rows[0]]
        st.button(f"Open {r['Project ID']} · {r['Project Name']} in Project Details →", type="primary",
                  on_click=open_project, args=(r["Project ID"],))
