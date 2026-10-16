import streamlit as st

from src import calculations as calc, charts, ui

TOP_N = 8


def render(ctx):
    p = ctx["data"]["projects"]
    if p.empty:
        return ui.no_data()
    top = p[p.is_active].sort_values("attention_score", ascending=False).head(TOP_N)
    if top.empty:
        return ui.no_data("No active projects match the current filters.")
    bands = calc.HEALTH_CONFIG["bands"]
    st.markdown(f"##### Top {len(top)} priority projects · health score (0-100)")
    st.caption(f"Ranked by management attention. Green ≥ {bands['On Track']} (On Track) · "
               f"amber ≥ {bands['At Risk']} (At Risk) · red below (Critical).")
    records = top.to_dict("records")
    for start in range(0, len(records), 4):
        for col, r in zip(st.columns(4), records[start:start + 4]):
            with col:
                ui.show(charts.health_gauge(r), f"gauge_{r['project_id']}")
