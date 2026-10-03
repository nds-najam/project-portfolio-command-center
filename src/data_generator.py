"""Deterministic synthetic data generator (all data is fictional).

generate(seed, scenario) -> dict of raw DataFrames: projects, issues, milestones, financials.
Derived fields (health, variances, attention) are added later by calculations.py.
"""
from datetime import timedelta

import numpy as np
import pandas as pd

from .config import (AS_OF, CLIENTS, REGIONS, MANAGERS, PROJECT_TYPES, ISSUE_CATEGORIES)

N_PROJECTS = 32

# Scenario knobs: probability / magnitude of delays, overruns, and issue volume.
SCENARIOS = {
    "Normal Portfolio":   dict(delay_p=0.30, delay_scale=1.0, over_p=0.20, over_scale=1.0, issue_mult=1.0, risk_bias=0.0),
    "Schedule Delay":     dict(delay_p=0.70, delay_scale=1.8, over_p=0.25, over_scale=1.0, issue_mult=1.3, risk_bias=0.1),
    "Cost Overrun":       dict(delay_p=0.30, delay_scale=1.0, over_p=0.65, over_scale=1.8, issue_mult=1.0, risk_bias=0.1),
    "High Risk Portfolio": dict(delay_p=0.60, delay_scale=1.5, over_p=0.55, over_scale=1.5, issue_mult=1.8, risk_bias=0.3),
}

NAME_ZONES = ["North", "South", "East", "West", "Central", "Industrial", "Corniche", "Ring Road", "Airport", "Northern"]
NAME_NOUNS = {
    "Fiber Deployment": "FTTH Fiber Rollout", "Network Upgrade": "Core Network Upgrade",
    "Tower Deployment": "Tower Build Program", "Civil Works": "Civil Works Package",
    "Infrastructure": "Infrastructure Program", "Enterprise Connectivity": "Enterprise Connectivity",
    "Maintenance": "Maintenance Contract",
}
MONTHLY_RATE_M = {  # contract value per month of duration, SAR millions (min, max)
    "Fiber Deployment": (0.8, 1.8), "Network Upgrade": (0.9, 1.9), "Tower Deployment": (0.7, 1.5),
    "Civil Works": (0.5, 1.2), "Infrastructure": (0.9, 2.0), "Enterprise Connectivity": (0.4, 1.0),
    "Maintenance": (0.2, 0.6),
}
ISSUE_TEMPLATES = {
    "Material Delay": ["Cable drums delayed at port", "Steel supply shortfall", "Equipment shipment held at customs"],
    "Resource Shortage": ["Insufficient installation crews", "Shortage of certified splicers", "Heavy equipment unavailable"],
    "Permit Delay": ["Municipality excavation permit pending", "Road-crossing approval delayed", "Site access permit expired"],
    "Client Dependency": ["Client site handover not confirmed", "Pending design sign-off from client", "Client power provisioning delayed"],
    "Design Change": ["Revised route design issued", "Scope change request under review", "Updated BoQ awaiting approval"],
    "Weather": ["Sandstorm stopped field works", "Heavy rain flooding trenches", "Extreme heat limiting work hours"],
    "Vendor Delay": ["Subcontractor mobilisation late", "Vendor testing equipment delayed", "Supplier delivery slipped"],
    "Access Issue": ["Landowner blocking site access", "Restricted-zone entry not granted", "Right-of-way dispute"],
    "Quality Issue": ["Failed OTDR test results", "Concrete strength non-conformance", "Rework required after audit"],
}
MILESTONE_NAMES = ["Mobilization", "Survey & Design Approval", "Permits & Approvals", "Material Delivery",
                   "Phase 1 Delivery", "Installation Complete", "Testing & Commissioning", "Final Handover"]
OWNER_ROLES = ["Site Manager", "Procurement Lead", "Planning Engineer", "Commercial Manager",
               "Quality Lead", "Client Liaison", "Operations Lead"]


def s_curve(t):
    """Smooth S-shaped progress curve, t in [0,1] -> [0,1]."""
    t = np.clip(t, 0, 1)
    return 3 * t**2 - 2 * t**3


def _inv_s_curve(p):
    """Inverse of s_curve via bisection (p in [0,1])."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if s_curve(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def generate(seed: int = 42, scenario: str = "Normal Portfolio") -> dict[str, pd.DataFrame]:
    sc = SCENARIOS[scenario]
    rng = np.random.default_rng(seed)           # scenario-independent attributes
    rs = np.random.default_rng(seed + 7919)     # scenario-dependent outcomes
    as_of = pd.Timestamp(AS_OF)
    n_completed = 6

    # ---------------- projects ----------------
    rows = []
    # evenly cycle clients/regions so every filter value is represented
    client_pool = rng.permutation([CLIENTS[i % len(CLIENTS)] for i in range(N_PROJECTS)])
    region_pool = rng.permutation([REGIONS[i % len(REGIONS)] for i in range(N_PROJECTS)])
    for i in range(N_PROJECTS):
        pid = f"P-{1001 + i}"
        ptype = PROJECT_TYPES[int(rng.integers(len(PROJECT_TYPES)))]
        region = region_pool[i]
        months = int(rng.integers(3, 25))
        dur = int(months * 30.4)
        lo, hi = MONTHLY_RATE_M[ptype]
        contract = round(months * rng.uniform(lo, hi) * 1e6, -3)
        completed = i < n_completed
        if completed:
            end = as_of - timedelta(days=int(rng.integers(10, 200)))
            start = end - timedelta(days=dur)
        else:
            frac = rng.uniform(0.12, 0.88)
            start = as_of - timedelta(days=int(dur * frac))
        planned_start = pd.Timestamp(start).normalize()
        planned_end = planned_start + timedelta(days=dur)

        # schedule variance (days behind plan; negative = ahead)
        if rs.random() < sc["delay_p"]:
            delay = int(rs.uniform(8, 55) * sc["delay_scale"])
        else:
            delay = int(rs.integers(-4, 7))
        if completed:
            delay = int(rs.integers(-5, 25))
        budget = round(contract * rng.uniform(0.80, 0.88), -3)
        if rs.random() < sc["over_p"]:
            over = rs.uniform(0.04, 0.13) * sc["over_scale"]
        else:
            over = rs.uniform(-0.04, 0.025)
        forecast_cost = round(budget * (1 + over), -3)

        actual_start = planned_start + timedelta(days=int(rng.integers(0, 8)))
        forecast_end = planned_end + timedelta(days=delay)
        if completed:
            completion, planned_pct = 100.0, 100.0
            spent = forecast_cost
        else:
            planned_pct = float(s_curve((as_of - planned_start).days / dur) * 100)
            t_eff = (as_of - planned_start).days - max(delay, 0) * (1 - 0.3)  # actual runs `delay` days behind
            completion = float(s_curve(t_eff / dur) * 100)
            completion = min(completion, 97.0)
            spent = forecast_cost * (completion / 100) * rs.uniform(0.98, 1.06)
            spent = min(spent, forecast_cost)
        rows.append(dict(
            project_id=pid,
            project_name=f"{region} {NAME_ZONES[int(rng.integers(len(NAME_ZONES)))]} {NAME_NOUNS[ptype]}",
            client=client_pool[i], region=region,
            project_manager=MANAGERS[int(rng.integers(len(MANAGERS)))],
            project_type=ptype, contract_value=contract, budget=budget,
            planned_start=planned_start, planned_end=planned_end,
            actual_start=actual_start, forecast_end=forecast_end,
            completion_percentage=round(completion, 1),
            planned_completion_percentage=round(planned_pct, 1),
            schedule_variance_days=delay, budget_spent=round(spent, -3),
            forecast_cost=forecast_cost, is_completed=completed,
            duration_days=dur, last_updated=as_of,
        ))
    projects = pd.DataFrame(rows)
    # make project names unique
    dup = projects.groupby("project_name").cumcount()
    projects["project_name"] = np.where(dup > 0, projects["project_name"] + " Ph" + (dup + 1).astype(str), projects["project_name"])

    # ---------------- issues & risks ----------------
    issues = []
    iid = 1
    for p in projects.itertuples():
        if p.is_completed:
            n_open_target = 0
        else:
            n_open_target = int(rs.poisson((1.2 + max(p.schedule_variance_days, 0) / 14) * sc["issue_mult"]))
        n_total = n_open_target + int(rs.integers(1, 4))  # plus some already-resolved ones
        for k in range(n_total):
            open_ = k < n_open_target
            is_risk = rs.random() < 0.35
            cat = ISSUE_CATEGORIES[int(rs.integers(len(ISSUE_CATEGORIES)))]
            # delayed projects skew toward critical items
            sev_p = np.array([0.08, 0.22, 0.45, 0.25]) + np.array([0.12, 0.08, -0.1, -0.1]) * min(max(p.schedule_variance_days, 0) / 40, 1) * sc["issue_mult"]
            sev_p = np.clip(sev_p, 0.01, None)
            sev = str(rs.choice(["Critical", "High", "Medium", "Low"], p=sev_p / sev_p.sum()))
            raised = as_of - timedelta(days=int(rs.integers(5, 90)))
            raised = max(raised, p.planned_start)
            if open_:
                due = as_of + timedelta(days=int(rs.integers(-25, 30)))
                status = str(rs.choice(["Open", "In Progress"], p=[0.45, 0.55]))
            else:
                due = raised + timedelta(days=int(rs.integers(7, 30)))
                status = str(rs.choice(["Resolved", "Closed"]))
            issues.append(dict(
                issue_id=f"I-{iid:04d}", project_id=p.project_id,
                item_type="Risk" if is_risk else "Issue",
                issue=ISSUE_TEMPLATES[cat][int(rs.integers(3))], category=cat, severity=sev,
                owner=OWNER_ROLES[int(rs.integers(len(OWNER_ROLES)))],
                raised_date=pd.Timestamp(raised).normalize(), due_date=pd.Timestamp(due).normalize(), status=status,
            ))
            iid += 1
    issues = pd.DataFrame(issues)
    open_mask = ~issues["status"].isin(["Resolved", "Closed"])
    projects["number_of_open_issues"] = projects["project_id"].map(
        issues[open_mask & (issues.item_type == "Issue")].groupby("project_id").size()).fillna(0).astype(int)
    projects["number_of_open_risks"] = projects["project_id"].map(
        issues[open_mask & (issues.item_type == "Risk")].groupby("project_id").size()).fillna(0).astype(int)

    # risk level: rule on delay, overrun, open critical/high items, plus scenario bias
    crit = issues[open_mask & issues.severity.isin(["Critical", "High"])].groupby("project_id").size()
    over_pct = (projects.forecast_cost - projects.budget) / projects.budget
    rscore = (projects.schedule_variance_days.clip(lower=0) / 30 + over_pct.clip(lower=0) / 0.08
              + projects.project_id.map(crit).fillna(0) * 0.5
              + rs.uniform(-0.3, 0.3, len(projects)) + sc["risk_bias"])
    projects["risk_level"] = np.where(rscore >= 1.8, "High", np.where(rscore >= 0.8, "Medium", "Low"))
    projects.loc[projects.is_completed, "risk_level"] = "Low"

    # ---------------- milestones ----------------
    ms = []
    mid = 1
    for p in projects.itertuples():
        n_ms = int(np.clip(round(p.duration_days / 70) + 3, 4, 8))
        names = [MILESTONE_NAMES[0]] + list(rs.choice(MILESTONE_NAMES[1:-1], n_ms - 2, replace=False)) + [MILESTONE_NAMES[-1]]
        order = {n: i for i, n in enumerate(MILESTONE_NAMES)}
        names.sort(key=lambda n: order[n])
        for j, name in enumerate(names):
            frac = (j + 1) / n_ms
            planned = p.planned_start + timedelta(days=int(p.duration_days * frac * 0.97))
            shift = int(max(p.schedule_variance_days, 0) * (0.4 + 0.6 * frac) + rs.integers(-2, 4))
            done = p.completion_percentage >= float(s_curve(frac * 0.97) * 100) + 1 or p.is_completed
            if done:
                status, date_ = "Completed", planned + timedelta(days=max(shift if p.schedule_variance_days > 0 else int(rs.integers(-3, 3)), -3))
                date_ = min(date_, as_of - timedelta(days=1)) if p.is_completed or date_ > as_of else date_
            else:
                date_ = planned + timedelta(days=max(shift, 0))
                if planned < as_of:
                    status = "Delayed"
                elif shift > 10:
                    status = "Delayed" if shift > 25 else "At Risk"
                elif shift > 4:
                    status = "At Risk"
                else:
                    status = "On Track"
            ms.append(dict(milestone_id=f"M-{mid:04d}", project_id=p.project_id, milestone=name,
                           planned_date=planned.normalize(), actual_forecast_date=pd.Timestamp(date_).normalize(), status=status))
            mid += 1
    milestones = pd.DataFrame(ms)

    # ---------------- financials / progress time series ----------------
    fin = []
    for p in projects.itertuples():
        horizon = p.planned_end + timedelta(days=max(p.schedule_variance_days, 0))
        end_obs = min(as_of, pd.Timestamp(horizon))
        step = max(7, p.duration_days // 24)
        dates = list(pd.date_range(p.planned_start, end_obs, freq=f"{step}D"))
        if dates[-1] != end_obs:
            dates.append(end_obs)
        lag = max(p.schedule_variance_days, 0) * 0.7
        final_actual_scale = None
        for d in dates:
            t_plan = (d - p.planned_start).days / p.duration_days
            planned_prog = float(s_curve(t_plan) * 100)
            actual_prog = float(s_curve(((d - p.planned_start).days - lag) / p.duration_days) * 100)
            fin.append(dict(project_id=p.project_id, period_end=d, planned_progress_pct=round(planned_prog, 1),
                            actual_progress_pct=actual_prog, planned_cum_cost=p.budget * planned_prog / 100))
        # rescale last actual so the series ends at the project's reported completion and spend
        sub = [r for r in fin if r["project_id"] == p.project_id]
        last = sub[-1]["actual_progress_pct"] or 1e-9
        for r in sub:
            r["actual_progress_pct"] = round(min(r["actual_progress_pct"] * p.completion_percentage / last, 100), 1)
            r["actual_cum_cost"] = round(p.budget_spent * r["actual_progress_pct"] / max(p.completion_percentage, 1e-9), 0)
            r["planned_cum_cost"] = round(r["planned_cum_cost"], 0)
    financials = pd.DataFrame(fin)

    return dict(projects=projects, issues=issues, milestones=milestones, financials=financials)
