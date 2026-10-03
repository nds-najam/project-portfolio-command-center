# Project Portfolio Command Center (POC)

A Streamlit proof-of-concept that gives contractor management a single-screen view of project health, schedule,
cost, issues and risks, with drill-down to individual projects.
**All data is synthetic** (fictional clients, managers and projects) - no real customer information is used.

## Business problem

Portfolio status usually lives in spreadsheets and status reports. Executives need to see in seconds how many
projects are active, which are on track, delayed or at risk, where budget is being consumed, and which projects need
management action today. This POC demonstrates that workflow:

Portfolio overview → identify at-risk projects → select project → understand schedule / cost / progress → identify issues → act.

## Architecture

```
Data Sources → Data Layer → Business Rules / KPI Layer → Dashboard → Management Insights
(synthetic)    data_loader   calculations.py              views/*      insights.py
               data_generator
```

```
project_dashboard/
├── app.py                  # entry point: sidebar navigation, global filters, page dispatch
├── requirements.txt
├── data/                   # CSVs written by the loader (projects, issues, milestones, financials)
├── src/
│   ├── config.py           # reference lists, colours, fixed "as of" date
│   ├── data_generator.py   # deterministic synthetic data + scenarios
│   ├── data_loader.py      # cached loading + filter cascade (swap point for real sources)
│   ├── calculations.py     # health score, attention score, variances, portfolio KPIs
│   ├── insights.py         # rule-based management insights (offline, no LLM)
│   ├── charts.py           # Plotly figure builders
│   └── ui.py               # CSS, KPI cards, table styling, empty-state helpers
└── views/                  # one module per page (named "views" so Streamlit does not auto-create pages)
```

## Features

- **Executive Dashboard** - KPI cards, portfolio story line, management attention cards, rule-based insights,
  health donut, status by client/region, planned vs actual completion, budget vs spend vs forecast, ranked attention table.
- **Project Portfolio** - filterable, colour-coded table with row selection and a jump to Project Details.
- **Project Details** - header, 8 KPI cards, planned vs actual progress, financials, milestones, issues/risks, health breakdown.
- **Issues & Risks** - KPIs, severity/category/client/region charts, overdue items table.
- **Schedule / Progress** - interactive Gantt (planned duration, forecast slip, today marker), variance histogram, delayed projects, milestone status.
- **Cost & Budget** - financial KPIs, budget vs spend, utilisation by client, forecast vs budget, overrun projects, register.
- **Data / Demo Controls** - scenarios, new dataset generation, health-score documentation, data preview and CSV download.
- Sidebar filters (client, region, manager, type, health, risk, date range) apply to every page. An empty selection means "all".
  Zero-row results show a friendly message instead of errors.

## Calculations (all transparent, configurable in `src/calculations.py`)

- Budget Variance = Budget − Forecast Cost (negative = overrun); Budget Utilization = Actual Spend ÷ Budget.
- Schedule variance = days forecast finish is behind planned finish (positive = late). "Delayed" = more than 7 days behind.
- **Health score (0-100)** = Schedule 30% + Cost 25% + Progress 25% + Open issues 10% + Risk 10%.
  Each component is 100 when fine and falls linearly to 0 at a configured limit (60 days late, 15% overrun,
  25 pts behind plan, 12 severity points, risk Low/Medium/High = 100/60/20).
  Bands: ≥ 80 On Track · 60-79 At Risk · < 60 Critical; 100% complete = Completed.
- **Attention score** (prioritisation, not a prediction): schedule 30 + cost 25 + progress gap 20 + critical issues 15 + risk 10.
- Overall completion is weighted by contract value.

## Data model

| File | Key columns |
|---|---|
| `projects.csv` | project_id, project_name, client, region, project_manager, project_type, contract_value, budget, planned_start, planned_end, actual_start, forecast_end, completion_percentage, planned_completion_percentage, schedule_variance_days, budget_spent, forecast_cost, risk_level, number_of_open_issues, number_of_open_risks, last_updated, plus derived health_score / health_status / attention_score / variances |
| `issues.csv` | issue_id, project_id, item_type (Issue/Risk), issue, category, severity, owner, raised_date, due_date, status |
| `milestones.csv` | milestone_id, project_id, milestone, planned_date, actual_forecast_date, status |
| `financials.csv` | project_id, period_end, planned/actual progress %, planned/actual cumulative cost (time series) |

## Install and run

macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Demo scenarios

Open **Data / Demo Controls**. The generator uses a fixed seed, so every run is identical; scenario parameters change
the probability and size of delays and overruns and the issue volume (project base attributes stay the same):

| Scenario | Effect |
|---|---|
| Normal Portfolio | ~30% of projects slip, ~20% overrun |
| Schedule Delay | ~70% slip, delays ×1.8, more issues |
| Cost Overrun | ~65% forecast above budget, overruns ×1.8 |
| High Risk Portfolio | delays, overruns, higher risk ratings and ~1.8× issues |

"Generate new demo dataset" increments the seed for a fresh random portfolio.

## Replacing the synthetic data

Edit `_fetch_raw()` in `src/data_loader.py` to return the four DataFrames from SQL Server, PostgreSQL, Excel, SAP, Oracle,
a REST API, a Power BI dataset or a project-management system. Calculations, insights and pages do not change.

## Future enhancements

Authentication and role-based views; real data connectors with scheduled refresh; baseline/re-baseline tracking; earned
value metrics (SPI/CPI); resource and subcontractor views; business-specific health rules or an ML model behind the
existing scoring interface; export to PDF/Excel; alerts and action tracking; optional LLM-written narrative on top of the rule-based insights.
