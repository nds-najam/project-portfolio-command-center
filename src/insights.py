"""Rule-based management insights (offline, no LLM). Each insight is (level, text); level in {'critical','warn','info'}."""
import pandas as pd

from . import calculations as calc
from .config import AS_OF


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def generate_insights(p: pd.DataFrame, issues: pd.DataFrame, milestones: pd.DataFrame) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if p is None or p.empty:
        return out
    act = p[p.is_active]

    over = act[act.forecast_cost > act.budget]
    if len(over):
        exp = (over.forecast_cost - over.budget).sum()
        out.append(("critical" if len(over) >= 5 else "warn",
                    f"{_plural(len(over), 'active project')} {'is' if len(over) == 1 else 'are'} forecast to exceed budget, "
                    f"a combined exposure of {calc.fmt_sar(exp)}."))

    delayed = act[act.is_delayed]
    if len(delayed):
        by_region = delayed.groupby("region").size().sort_values(ascending=False)
        top = by_region.index[0]
        out.append(("warn", f"{top} region has the highest number of delayed projects ({by_region.iloc[0]} of {len(delayed)} delayed)."))

    if len(act):
        worst = act.sort_values("schedule_variance_days", ascending=False).iloc[0]
        if worst.schedule_variance_days > calc.DELAY_THRESHOLD_DAYS:
            out.append(("critical", f"Project {worst.project_id} is {worst.schedule_variance_days} days behind schedule "
                                    f"while consuming {worst.budget_utilization:.0%} of its budget."))
        # progress vs spend mismatch
        burn = act[(act.budget_utilization - act.completion_percentage / 100) > 0.10]
        if len(burn):
            b = burn.assign(g=burn.budget_utilization - burn.completion_percentage / 100).sort_values("g", ascending=False).iloc[0]
            out.append(("warn", f"{_plural(len(burn), 'project')} are spending faster than they are progressing; "
                                f"{b.project_id} has used {b.budget_utilization:.0%} of budget for {b.completion_percentage:.0f}% completion."))

    att = act[act.attention_score >= calc.ATTENTION_MIN_SCORE]
    if len(att):
        by_client = att.groupby("client").size().sort_values(ascending=False)
        out.append(("warn", f"{by_client.index[0]} has {_plural(by_client.iloc[0], 'project')} requiring immediate management attention."))
        by_mgr = att.groupby("project_manager").size().sort_values(ascending=False)
        if by_mgr.iloc[0] >= 2:
            out.append(("info", f"{by_mgr.index[0]} manages {by_mgr.iloc[0]} of the projects flagged for attention."))

    risky = act[act.risk_level == "High"]
    if len(risky):
        r = risky.groupby("client").size().sort_values(ascending=False)
        out.append(("info", f"{_plural(len(risky), 'project')} carry a High risk rating; {r.index[0]} has the most ({r.iloc[0]})."))

    op = calc.open_items(issues)
    if not op.empty:
        overdue_crit = op[(op.severity == "Critical") & (op.due_date < pd.Timestamp(AS_OF))]
        if len(overdue_crit):
            out.append(("critical", f"{_plural(len(overdue_crit), 'critical issue')} {'is' if len(overdue_crit) == 1 else 'are'} overdue."))
        iss = op[op.item_type == "Issue"]
        if not iss.empty:
            c = iss.category.value_counts()
            out.append(("info", f"'{c.index[0]}' is the most common open issue category ({c.iloc[0]} open issues)."))

    if milestones is not None and not milestones.empty:
        dm = milestones[milestones.status == "Delayed"]
        if len(dm):
            out.append(("warn", f"{_plural(len(dm), 'milestone')} across {dm.project_id.nunique()} projects are past their planned date."))

    if not out:
        out.append(("info", "No significant exceptions detected for the current selection."))
    return out
