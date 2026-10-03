"""Streamlit presentation helpers: CSS, KPI cards, table styling, empty-state handling."""
import pandas as pd
import streamlit as st

from .config import COLORS

CSS = """
<style>
html, body, [class*="css"] { font-family: Inter, 'Segoe UI', Helvetica, Arial, sans-serif; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }
.app-header { background: linear-gradient(100deg,#14233A 0%,#1F3A5F 100%); color:#fff; padding:18px 24px;
  border-radius:10px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; gap:16px; }
.app-header h1 { font-size:1.35rem; letter-spacing:.12em; margin:0; font-weight:700; color:#fff; padding:0; }
.app-header p { margin:4px 0 0 0; color:#B8C7DB; font-size:.9rem; }
.badge { background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.35); padding:5px 12px; border-radius:20px;
  font-size:.75rem; font-weight:600; letter-spacing:.06em; white-space:nowrap; }
.kpi { background:#fff; border:1px solid #E3E8EF; border-radius:10px; padding:12px 14px; border-left:4px solid #2F6DB5;
  min-height:92px; }
.kpi .l { color:#6B7A90; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; }
.kpi .v { color:#1B2A41; font-size:1.55rem; font-weight:700; line-height:1.25; }
.kpi .s { color:#6B7A90; font-size:.75rem; }
.kpi.green { border-left-color:#2E8B63; } .kpi.amber { border-left-color:#E0A526; }
.kpi.red { border-left-color:#C8483A; } .kpi.grey { border-left-color:#7C8DA6; }
.section { font-size:.8rem; text-transform:uppercase; letter-spacing:.1em; color:#6B7A90; font-weight:700;
  border-bottom:1px solid #E3E8EF; padding-bottom:4px; margin:22px 0 10px 0; }
.insight { padding:8px 12px; border-radius:6px; margin-bottom:6px; font-size:.9rem; color:#1B2A41; background:#F4F7FB;
  border-left:4px solid #2F6DB5; }
.insight.critical { border-left-color:#C8483A; background:#FBF1EF; }
.insight.warn { border-left-color:#E0A526; background:#FDF8EC; }
.attn { border:1px solid #E3E8EF; border-left:4px solid #C8483A; border-radius:8px; padding:10px 14px; background:#fff; margin-bottom:8px; }
.attn b { color:#1B2A41; } .attn span { color:#4A5A70; font-size:.85rem; }
.pill { display:inline-block; padding:2px 10px; border-radius:12px; font-size:.78rem; font-weight:700; color:#fff; }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header():
    st.markdown(
        """<div class="app-header"><div><h1>PROJECT PORTFOLIO COMMAND CENTER</h1>
        <p>Executive visibility across projects, schedule, cost, risks and delivery performance</p></div>
        <div class="badge">DEMO DATA | POC</div></div>""", unsafe_allow_html=True)


def section(title: str):
    st.markdown(f'<div class="section">{title}</div>', unsafe_allow_html=True)


def kpi_cards(items: list[tuple], per_row: int = 4):
    """items: (label, value, sub, tone) with tone in '', green, amber, red, grey."""
    for i in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for col, (label, value, sub, tone) in zip(cols, items[i:i + per_row]):
            col.markdown(f'<div class="kpi {tone}"><div class="l">{label}</div><div class="v">{value}</div>'
                         f'<div class="s">{sub or "&nbsp;"}</div></div>', unsafe_allow_html=True)


def no_data(msg: str = "No projects match the current filters. Adjust or reset the filters in the sidebar."):
    st.info(msg, icon="ℹ️")


def show(fig, key: str, empty_msg: str = "No data available for this view."):
    if fig is None:
        st.caption(f"_{empty_msg}_")
    else:
        st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def insight_box(insights):
    for level, text in insights:
        st.markdown(f'<div class="insight {level}">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- table styling
_HEALTH_BG = {"On Track": "#DCF0E5", "At Risk": "#FBEFC9", "Critical": "#F6D6D1", "Completed": "#E3E8EF"}
_RISK_BG = {"Low": "#DCF0E5", "Medium": "#FBEFC9", "High": "#F6D6D1"}
_SEV_BG = {"Critical": "#F6D6D1", "High": "#FBE0CC", "Medium": "#FBEFC9", "Low": "#E3E8EF"}
_MS_BG = {"Completed": "#E3E8EF", "On Track": "#DCF0E5", "At Risk": "#FBEFC9", "Delayed": "#F6D6D1"}


def _bg(mapping):
    return lambda v: f"background-color: {mapping[v]}; font-weight: 600;" if v in mapping else ""


def _days(v):
    if pd.isna(v):
        return ""
    return "background-color:#F6D6D1;" if v > 14 else "background-color:#FBEFC9;" if v > 7 else ""


def _budget_var(v):  # percent, negative = overrun
    if pd.isna(v):
        return ""
    return "background-color:#F6D6D1;" if v < -5 else "background-color:#FBEFC9;" if v < 0 else ""


def style_table(df: pd.DataFrame, health=(), risk=(), severity=(), ms=(), days=(), budget_var=(), formats=None):
    s = df.style
    for cols, mapping in [(health, _HEALTH_BG), (risk, _RISK_BG), (severity, _SEV_BG), (ms, _MS_BG)]:
        cols = [c for c in cols if c in df.columns]
        if cols:
            s = s.map(_bg(mapping), subset=cols)
    if [c for c in days if c in df.columns]:
        s = s.map(_days, subset=[c for c in days if c in df.columns])
    if [c for c in budget_var if c in df.columns]:
        s = s.map(_budget_var, subset=[c for c in budget_var if c in df.columns])
    if formats:
        s = s.format({k: v for k, v in formats.items() if k in df.columns}, na_rep="–")
    return s
