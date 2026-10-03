import streamlit as st

from src import calculations as calc, charts, ui


def render(ctx):
    d = ctx["data"]
    p = d["projects"]
    ui.section("Schedule & progress")
    if p.empty:
        return ui.no_data()
    act = p[p.is_active]
    if act.empty:
        return st.info("No active projects in the current selection.", icon="ℹ️")
    ms = d["milestones"]
    ui.kpi_cards([
        ("Active Projects", f"{len(act)}", "", ""),
        ("Delayed Projects", f"{int(act.is_delayed.sum())}", f"> {calc.DELAY_THRESHOLD_DAYS} days behind", "red"),
        ("Avg Schedule Variance", f"{act.schedule_variance_days.mean():+.0f} days", "active projects", "amber"),
        ("Overdue Milestones", f"{int((ms.status == 'Delayed').sum()) if not ms.empty else 0}", "past planned date", "red"),
    ])
    tab1, tab2, tab3 = st.tabs(["Gantt timeline", "Progress & variance", "Delayed projects & milestones"])
    with tab1:
        st.caption("Planned duration coloured by health; red outline = forecast slip beyond planned end. Highest-priority projects first.")
        ui.show(charts.gantt(p), "sc_gantt")
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Planned vs actual completion % (largest gaps)")
            ui.show(charts.schedule_performance(p), "sc_perf")
        with c2:
            st.caption("Schedule variance distribution")
            ui.show(charts.variance_hist(p), "sc_hist")
    with tab3:
        c1, c2 = st.columns([1.6, 1])
        with c1:
            dl = act[act.is_delayed].sort_values("schedule_variance_days", ascending=False)
            if dl.empty:
                st.success("No delayed projects.")
            else:
                t = dl.assign(Project=dl.project_id + " · " + dl.project_name)[
                    ["Project", "client", "region", "project_manager", "completion_percentage", "schedule_variance_days", "planned_end", "forecast_end"]]
                t.columns = ["Project", "Client", "Region", "Manager", "Completion", "Schedule Variance", "Planned End", "Forecast End"]
                st.dataframe(ui.style_table(t, days=["Schedule Variance"], formats={"Schedule Variance": "{:+.0f} d"}),
                             hide_index=True, width="stretch", height=min(60 + 35 * len(t), 480),
                             column_config={"Completion": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
                                            "Planned End": st.column_config.DateColumn(format="DD MMM YYYY"),
                                            "Forecast End": st.column_config.DateColumn(format="DD MMM YYYY")})
        with c2:
            st.caption("Milestone status")
            ui.show(charts.milestone_status_bar(ms), "sc_ms", "No milestone data available.")
