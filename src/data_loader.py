"""Data layer. The dashboard only talks to load_data() and filter_data().

To use real data, replace the body of `_fetch_raw` (SQL Server, PostgreSQL, Excel, SAP, Oracle,
REST API, Power BI dataset ...) so it returns the same four DataFrames
(projects, issues, milestones, financials) with the columns documented in the README.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from . import calculations as calc
from .data_generator import generate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMPTY_KEYS = ("projects", "issues", "milestones", "financials")


def _fetch_raw(seed: int, scenario: str) -> dict[str, pd.DataFrame]:
    return generate(seed, scenario)  # <-- swap for a real data source


@st.cache_data(show_spinner=False)
def load_data(seed: int, scenario: str) -> dict[str, pd.DataFrame]:
    raw = _fetch_raw(seed, scenario)
    raw["projects"] = calc.enrich_projects(raw["projects"], raw["issues"], raw["milestones"])
    try:  # persist CSVs so the data can be inspected / opened in Excel
        DATA_DIR.mkdir(exist_ok=True)
        for k in EMPTY_KEYS:
            raw[k].to_csv(DATA_DIR / f"{k}.csv", index=False)
    except OSError:
        pass
    return raw


def filter_data(data: dict, f: dict) -> dict:
    """Apply sidebar filters (empty selection = no restriction) and cascade to child tables."""
    p = data.get("projects", pd.DataFrame())
    if p is None or p.empty:
        return {k: data.get(k, pd.DataFrame()) for k in EMPTY_KEYS}
    mask = pd.Series(True, index=p.index)
    for col, key in [("client", "client"), ("region", "region"), ("project_manager", "manager"),
                     ("project_type", "ptype"), ("health_status", "health"), ("risk_level", "risk")]:
        if f.get(key):
            mask &= p[col].isin(f[key])
    if f.get("date_range") and len(f["date_range"]) == 2:  # projects overlapping the window
        lo, hi = (pd.Timestamp(d) for d in f["date_range"])
        mask &= (p.planned_start <= hi) & (p.forecast_end >= lo)
    p = p[mask]
    out = {"projects": p}
    for k in ("issues", "milestones", "financials"):
        df = data.get(k)
        out[k] = df[df.project_id.isin(p.project_id)] if df is not None and not df.empty and "project_id" in df else \
            pd.DataFrame(columns=df.columns if df is not None else [])
    return out
