# CLAUDE.md

Streamlit POC: "Project Portfolio Command Center" for a contractor (sales demo). All data is synthetic; never add real customer data.

## Run
```
pip install -r requirements.txt
streamlit run app.py
```
Windows note: a fresh `.venv` may be blocked by Application Control (pandas DLL); the global Python works.

## Architecture
Data Sources → `src/data_loader.py` → `src/calculations.py` → `views/*` → `src/insights.py`
- `app.py`: sidebar nav (`st.session_state["nav"]`), global filters, dispatches `views/<page>.render(ctx)` with `ctx = {"data": filtered, "full": unfiltered}`.
- `views/` (not `pages/`, to avoid Streamlit's auto-multipage): one module per page.
- `src/data_generator.py`: deterministic (seed + scenario). Scenario-independent attributes use `rng`, scenario-dependent outcomes use `rs` — keep that split so scenarios reshape the same portfolio.
- `src/data_loader.py`: `_fetch_raw()` is the swap point for real data; `load_data` is `@st.cache_data` keyed on (seed, scenario) and rewrites `data/*.csv`.
- `src/calculations.py`: all business rules. `HEALTH_CONFIG` (weights/limits/bands) and `ATTENTION_CONFIG` are the tunables. Health bands: >=80 On Track, 60-79 At Risk, <60 Critical; 100% complete = Completed. "Delayed" = >7 days behind.
- `src/charts.py`: Plotly builders returning a Figure or `None` when empty; render via `ui.show`.
- `src/insights.py`: rule-based insights, no LLM.

## Conventions
- Every page must handle empty DataFrames (show `ui.no_data()` / friendly caption), never crash on zero rows.
- Filter option lists come from `src/config.py` constants, not data, so stale widget state can't break on dataset change. Empty multiselect = all.
- Fixed reporting date `config.AS_OF`; don't use `date.today()`.
- Schedule variance: days late, positive = behind. Budget variance = budget − forecast (negative = overrun).
- Status colours are reserved (green/amber/red); keep palettes in `config.COLORS`.

## Testing
Headless check of all pages/scenarios/filters via `streamlit.testing.v1.AppTest` (loop over nav pages, assert `at.exception` is empty).
