"""Business rules / KPI layer: variances, health score, attention score, portfolio KPIs.

Everything here is plain, transparent arithmetic driven by the config dicts below.
Replace the config values (or the scoring functions) with real business rules or a model later.
"""
import numpy as np
import pandas as pd

from .config import AS_OF

# ---------------------------------------------------------------- configuration
HEALTH_CONFIG = {
    "weights": {"schedule": 0.30, "cost": 0.25, "progress": 0.25, "issues": 0.10, "risk": 0.10},
    # value at which each component score reaches 0 (score is 100 at/below "no problem")
    "zero_at": {
        "schedule_days_late": 60,       # days behind schedule
        "cost_overrun_pct": 0.15,       # forecast cost over budget (fraction)
        "progress_gap_pts": 25,         # planned% - actual% in percentage points
        "issue_points": 12,             # weighted open issues (see ISSUE_POINTS)
    },
    "risk_scores": {"Low": 100, "Medium": 60, "High": 20},
    "bands": {"On Track": 80, "At Risk": 60},   # >=80 On Track, 60-79 At Risk, <60 Critical
}
ISSUE_POINTS = {"Critical": 4, "High": 2, "Medium": 1, "Low": 0.5}

ATTENTION_CONFIG = {  # max points per factor (total 100) and the value that earns the max
    "schedule": (30, 45),      # days behind
    "cost": (25, 0.12),        # forecast overrun fraction
    "progress": (20, 20),      # progress gap in points
    "critical_issues": (15, 3),  # open critical issues (count)
    "risk": {"Low": 0, "Medium": 5, "High": 10},
}
DELAY_THRESHOLD_DAYS = 7      # a project counts as "Delayed" beyond this many days behind
ATTENTION_MIN_SCORE = 25      # below this a project is not listed as needing attention
CLOSED = ["Resolved", "Closed"]


def _lin(value, zero_at):
    """100 when value<=0, 0 when value>=zero_at, linear in between."""
    return float(np.clip(100 * (1 - value / zero_at), 0, 100))


def open_items(issues: pd.DataFrame) -> pd.DataFrame:
    if issues is None or issues.empty:
        return pd.DataFrame(columns=["project_id", "severity", "item_type", "due_date", "status", "category"])
    return issues[~issues["status"].isin(CLOSED)]


def enrich_projects(projects: pd.DataFrame, issues: pd.DataFrame, milestones: pd.DataFrame) -> pd.DataFrame:
    """Add variances, health score/status and attention score to the raw project table."""
    df = projects.copy()
    if df.empty:
        return df
    cfg = HEALTH_CONFIG
    df["budget_variance"] = df["budget"] - df["forecast_cost"]                      # + = under budget
    df["budget_variance_pct"] = df["budget_variance"] / df["budget"]
    df["cost_overrun_pct"] = (-df["budget_variance_pct"]).clip(lower=0)
    df["budget_utilization"] = df["budget_spent"] / df["budget"]
    df["progress_gap"] = df["planned_completion_percentage"] - df["completion_percentage"]

    op = open_items(issues)
    crit = op[op.severity == "Critical"].groupby("project_id").size()
    pts = op.assign(p=op.severity.map(ISSUE_POINTS)).groupby("project_id")["p"].sum()
    df["open_critical_issues"] = df["project_id"].map(crit).fillna(0).astype(int)
    df["issue_points"] = df["project_id"].map(pts).fillna(0.0)
    od_ms = pd.Series(dtype=int) if milestones is None or milestones.empty else \
        milestones[milestones.status == "Delayed"].groupby("project_id").size()
    df["overdue_milestones"] = df["project_id"].map(od_ms).fillna(0).astype(int)

    z = cfg["zero_at"]
    df["score_schedule"] = df["schedule_variance_days"].apply(lambda v: _lin(v, z["schedule_days_late"]))
    df["score_cost"] = df["cost_overrun_pct"].apply(lambda v: _lin(v, z["cost_overrun_pct"]))
    df["score_progress"] = df["progress_gap"].apply(lambda v: _lin(v, z["progress_gap_pts"]))
    df["score_issues"] = df["issue_points"].apply(lambda v: _lin(v, z["issue_points"]))
    df["score_risk"] = df["risk_level"].map(cfg["risk_scores"]).astype(float)
    w = cfg["weights"]
    df["health_score"] = (df.score_schedule * w["schedule"] + df.score_cost * w["cost"] + df.score_progress * w["progress"]
                          + df.score_issues * w["issues"] + df.score_risk * w["risk"]).round(1)
    b = cfg["bands"]
    df["health_status"] = np.where(df.health_score >= b["On Track"], "On Track",
                                   np.where(df.health_score >= b["At Risk"], "At Risk", "Critical"))
    df.loc[df.completion_percentage >= 100, "health_status"] = "Completed"
    df["is_active"] = df["health_status"] != "Completed"
    df["is_delayed"] = df.is_active & (df.schedule_variance_days > DELAY_THRESHOLD_DAYS)

    # ---- attention score (prioritisation only, not a prediction)
    a = ATTENTION_CONFIG
    df["attention_score"] = (
        (df.schedule_variance_days.clip(lower=0) / a["schedule"][1]).clip(upper=1) * a["schedule"][0]
        + (df.cost_overrun_pct / a["cost"][1]).clip(upper=1) * a["cost"][0]
        + (df.progress_gap.clip(lower=0) / a["progress"][1]).clip(upper=1) * a["progress"][0]
        + (df.open_critical_issues / a["critical_issues"][1]).clip(upper=1) * a["critical_issues"][0]
        + df.risk_level.map(a["risk"])
    ).round(1)
    df.loc[~df.is_active, "attention_score"] = 0.0
    return df


def top_issue_category(issues: pd.DataFrame) -> pd.Series:
    """Most common category among overdue/critical open items per project (used in reasons)."""
    op = open_items(issues)
    if op.empty:
        return pd.Series(dtype=str)
    op = op[(op.due_date < pd.Timestamp(AS_OF)) | (op.severity == "Critical")]
    if op.empty:
        return pd.Series(dtype=str)
    return op.groupby("project_id")["category"].agg(lambda s: s.value_counts().index[0])


def attention_table(projects: pd.DataFrame, issues: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Ranked list of active projects needing management attention, with readable reasons."""
    cols = ["Priority", "project_id", "Project", "Client", "Region", "Progress", "Schedule Variance",
            "Budget Variance", "Risk", "Open Issues", "Critical Issues", "Reason", "Recommended Attention",
            "Attention Score"]
    if projects is None or projects.empty:
        return pd.DataFrame(columns=cols)
    df = projects[projects.is_active & (projects.attention_score >= ATTENTION_MIN_SCORE)]
    df = df.sort_values("attention_score", ascending=False).head(top_n).copy()
    if df.empty:
        return pd.DataFrame(columns=cols)
    cat = top_issue_category(issues)
    reasons, actions = [], []
    for r in df.itertuples():
        parts = []
        if r.schedule_variance_days > DELAY_THRESHOLD_DAYS:
            parts.append(f"{r.schedule_variance_days} days behind schedule")
        if r.cost_overrun_pct > 0.02:
            parts.append(f"{r.cost_overrun_pct:.0%} forecast cost overrun")
        if r.open_critical_issues:
            parts.append(f"{r.open_critical_issues} critical issue{'s' if r.open_critical_issues > 1 else ''}")
        if r.overdue_milestones:
            parts.append(f"{r.overdue_milestones} overdue milestone{'s' if r.overdue_milestones > 1 else ''}")
        if r.progress_gap > 10 and not parts:
            parts.append(f"{r.progress_gap:.0f} pts behind planned progress")
        if r.project_id in cat.index:
            parts.append(f"driver: {cat[r.project_id]}")
        reasons.append(" + ".join(parts) or "High cumulative risk exposure")
        # recommended action = largest scoring factor
        sched = min(max(r.schedule_variance_days, 0) / 45, 1) * 30
        cost = min(r.cost_overrun_pct / 0.12, 1) * 25
        crit = min(r.open_critical_issues / 3, 1) * 15
        top = max([(sched, "Agree schedule recovery plan"), (cost, "Cost containment review"),
                   (crit, "Escalate critical issues to steering committee")], key=lambda x: x[0])
        actions.append(top[1])
    df["Reason"], df["Recommended Attention"] = reasons, actions
    df["Priority"] = range(1, len(df) + 1)
    out = pd.DataFrame({
        "Priority": df["Priority"], "project_id": df["project_id"],
        "Project": df["project_id"] + " · " + df["project_name"], "Client": df["client"], "Region": df["region"],
        "Progress": df["completion_percentage"], "Schedule Variance": df["schedule_variance_days"],
        "Budget Variance": df["budget_variance_pct"] * 100, "Risk": df["risk_level"],
        "Open Issues": df["number_of_open_issues"], "Critical Issues": df["open_critical_issues"],
        "Reason": df["Reason"], "Recommended Attention": df["Recommended Attention"],
        "Attention Score": df["attention_score"],
    })
    return out.reset_index(drop=True)


def portfolio_kpis(p: pd.DataFrame) -> dict:
    """Headline KPIs for a (filtered) enriched project table. Safe on empty input."""
    if p is None or p.empty:
        return dict(total=0, active=0, on_track=0, at_risk=0, critical=0, delayed=0, completed=0,
                    contract_value=0.0, budget=0.0, spent=0.0, forecast=0.0, utilization=0.0,
                    completion=0.0, exposure=0.0, overrun_projects=0)
    act = p[p.is_active]
    budget = p.budget.sum()
    over = p[p.forecast_cost > p.budget]
    return dict(
        total=len(p), active=len(act),
        on_track=int((p.health_status == "On Track").sum()), at_risk=int((p.health_status == "At Risk").sum()),
        critical=int((p.health_status == "Critical").sum()), completed=int((p.health_status == "Completed").sum()),
        delayed=int(p.is_delayed.sum()),
        contract_value=p.contract_value.sum(), budget=budget, spent=p.budget_spent.sum(),
        forecast=p.forecast_cost.sum(), utilization=p.budget_spent.sum() / budget if budget else 0.0,
        # contract-value weighted completion
        completion=float((p.completion_percentage * p.contract_value).sum() / p.contract_value.sum()) if p.contract_value.sum() else 0.0,
        exposure=float((over.forecast_cost - over.budget).sum()), overrun_projects=len(over),
    )


def fmt_sar(v: float) -> str:
    v = float(v)
    if abs(v) >= 1e9:
        return f"SAR {v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"SAR {v / 1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"SAR {v / 1e3:.0f}K"
    return f"SAR {v:.0f}"
