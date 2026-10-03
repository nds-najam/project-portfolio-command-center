"""Project Portfolio Command Center - Streamlit POC entry point.  Run: streamlit run app.py"""
from datetime import date

import streamlit as st

st.set_page_config(page_title="Project Portfolio Command Center", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

from src import config, data_loader, ui  # noqa: E402
from views import (demo_controls, executive_dashboard, financials, issues, portfolio,  # noqa: E402
                   project_details, schedule)

PAGES = {
    "Executive Dashboard": executive_dashboard,
    "Project Portfolio": portfolio,
    "Project Details": project_details,
    "Issues & Risks": issues,
    "Schedule / Progress": schedule,
    "Cost & Budget": financials,
    "Data / Demo Controls": demo_controls,
}
FILTER_KEYS = {"f_client": [], "f_region": [], "f_manager": [], "f_ptype": [], "f_health": [], "f_risk": []}
DATE_MIN, DATE_MAX = date(2024, 1, 1), date(2029, 12, 31)

# ---- session defaults
st.session_state.setdefault("scenario", "Normal Portfolio")
st.session_state.setdefault("seed", 42)
st.session_state.setdefault("nav", "Executive Dashboard")

data = data_loader.load_data(st.session_state["seed"], st.session_state["scenario"])
projects = data["projects"]
span = (max(DATE_MIN, projects.planned_start.min().date()), min(DATE_MAX, projects.forecast_end.max().date())) \
    if not projects.empty else (DATE_MIN, DATE_MAX)


def reset_filters():
    for k, v in FILTER_KEYS.items():
        st.session_state[k] = list(v)
    st.session_state["f_dates"] = span


if st.session_state.pop("reset_filters", False) or "f_dates" not in st.session_state:
    reset_filters()

ui.inject_css()

with st.sidebar:
    st.markdown("### 📊 Command Center")
    st.radio("Dashboard", list(PAGES), key="nav", label_visibility="collapsed")
    st.divider()
    st.markdown("**Filters**")
    st.multiselect("Client", config.CLIENTS, key="f_client", placeholder="All clients")
    st.multiselect("Region", config.REGIONS, key="f_region", placeholder="All regions")
    st.multiselect("Project Manager", config.MANAGERS, key="f_manager", placeholder="All managers")
    st.multiselect("Project Type", config.PROJECT_TYPES, key="f_ptype", placeholder="All types")
    st.multiselect("Health Status", config.HEALTH_STATUSES, key="f_health", placeholder="All statuses")
    st.multiselect("Risk Level", config.RISK_LEVELS, key="f_risk", placeholder="All risk levels")
    st.date_input("Project date range", key="f_dates", min_value=DATE_MIN, max_value=DATE_MAX,
                  help="Shows projects whose planned start to forecast end overlaps this window.")
    st.button("Reset Filters", on_click=reset_filters, width="stretch")
    st.divider()
    st.caption(f"Scenario: **{st.session_state['scenario']}**")
    st.caption(f"Data last updated: **{config.AS_OF:%d %b %Y}**  \nDemo data | POC")

filters = dict(client=st.session_state["f_client"], region=st.session_state["f_region"],
               manager=st.session_state["f_manager"], ptype=st.session_state["f_ptype"],
               health=st.session_state["f_health"], risk=st.session_state["f_risk"],
               date_range=st.session_state["f_dates"] if len(st.session_state["f_dates"]) == 2 else None)
filtered = data_loader.filter_data(data, filters)

ui.header()
PAGES[st.session_state["nav"]].render({"data": filtered, "full": data})
