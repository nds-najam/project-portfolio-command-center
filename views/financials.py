import streamlit as st

from src import calculations as calc, charts, ui


def render(ctx):
    p = ctx["data"]["projects"]
    ui.section("Cost & budget")
    if p.empty:
        return ui.no_data()
    k = calc.portfolio_kpis(p)
    remaining = k["budget"] - k["spent"]
    var = k["budget"] - k["forecast"]
    ui.kpi_cards([
        ("Total Contract Value", calc.fmt_sar(k["contract_value"]), "", ""),
        ("Total Budget", calc.fmt_sar(k["budget"]), "", ""),
        ("Actual Spend", calc.fmt_sar(k["spent"]), f"{k['utilization']:.0%} utilization", ""),
        ("Forecast Cost", calc.fmt_sar(k["forecast"]), f"{'Overrun' if var < 0 else 'Headroom'} {calc.fmt_sar(abs(var))} vs budget", "red" if var < 0 else "green"),
        ("Budget Remaining", calc.fmt_sar(remaining), "budget − actual spend", ""),
        ("Projects Over Budget", f"{k['overrun_projects']}", f"exposure {calc.fmt_sar(k['exposure'])}", "red" if k["overrun_projects"] else "green"),
    ], per_row=3)
    st.caption("Budget Variance = Budget − Forecast Cost (negative = overrun) · Budget Utilization = Actual Spend ÷ Budget")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Budget vs actual spend by project (largest budgets)")
        ui.show(charts.budget_by_project(p), "fn_proj")
        st.caption("Forecast cost vs budget (points above the line exceed budget)")
        ui.show(charts.forecast_vs_budget(p), "fn_scatter")
    with c2:
        st.caption("Budget utilization by client")
        ui.show(charts.utilization_by_client(p), "fn_util")
        st.caption("Projects with forecast cost overrun (SAR M)")
        ui.show(charts.overrun_bars(p), "fn_over", "No projects are forecast to exceed budget.")

    ui.section("Project financial register")
    t = p.sort_values("budget_variance")
    t = t.assign(Project=t.project_id + " · " + t.project_name, util=t.budget_utilization * 100, var_pct=t.budget_variance_pct * 100)
    t = t[["Project", "client", "contract_value", "budget", "budget_spent", "forecast_cost", "budget_variance", "var_pct", "util"]]
    t.columns = ["Project", "Client", "Contract Value", "Budget", "Actual Spend", "Forecast Cost", "Budget Variance", "Variance %", "Utilization"]
    money = "{:,.0f}"
    st.dataframe(ui.style_table(t, budget_var=["Variance %"], formats={
        "Contract Value": money, "Budget": money, "Actual Spend": money, "Forecast Cost": money,
        "Budget Variance": "{:+,.0f}", "Variance %": "{:+.1f}%", "Utilization": "{:.0f}%"}),
        hide_index=True, width="stretch", height=420)
    st.caption("All amounts in SAR. Highlighted rows: forecast cost exceeds budget (amber < 0%, red beyond −5%).")
