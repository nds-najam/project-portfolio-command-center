"""Plotly figure builders. Every function returns a Figure, or None when there is nothing to plot."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .config import (AS_OF, COLORS, HEALTH_STATUSES, SEVERITIES, SEVERITY_COLORS, MILESTONE_COLORS)

FONT = "Inter, Segoe UI, Helvetica, Arial, sans-serif"
SERIES = {"Budget": "#8FA3BF", "Actual Spend": "#2F6DB5", "Forecast Cost": "#1B2A41",
          "Planned": "#8FA3BF", "Actual": "#2F6DB5"}


def _style(fig, height=340, legend=True, title=None):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=36 if title else 10, b=10),
        title=dict(text=title, font=dict(size=14, color=COLORS["Ink"]), x=0) if title else None,
        font=dict(family=FONT, size=12, color=COLORS["Ink"]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=legend,
        legend=dict(orientation="h", y=-0.18, x=0, title=None, font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", font_size=12), bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["Grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["Grid"], zeroline=False, linecolor=COLORS["Grid"])
    return fig


def _empty(df):
    return df is None or len(df) == 0


def health_donut(p):
    if _empty(p):
        return None
    c = p["health_status"].value_counts().reindex(HEALTH_STATUSES).fillna(0).astype(int)
    c = c[c > 0]
    fig = go.Figure(go.Pie(labels=c.index, values=c.values, hole=0.62, sort=False,
                           marker=dict(colors=[COLORS[k] for k in c.index], line=dict(color="white", width=2)),
                           textinfo="value", textfont=dict(size=13, color="white"),
                           hovertemplate="%{label}: %{value} projects (%{percent})<extra></extra>"))
    fig.add_annotation(text=f"<b>{len(p)}</b><br><span style='font-size:11px;color:{COLORS['Muted']}'>projects</span>",
                       showarrow=False, font=dict(size=24, color=COLORS["Ink"]))
    return _style(fig, 320)


def status_stack(p, by, horizontal=False):
    if _empty(p):
        return None
    t = p.groupby([by, "health_status"]).size().reset_index(name="projects")
    order = p.groupby(by).size().sort_values(ascending=horizontal).index.tolist()
    fig = px.bar(t, x="projects" if horizontal else by, y=by if horizontal else "projects", color="health_status",
                 color_discrete_map=COLORS, category_orders={"health_status": HEALTH_STATUSES, by: order},
                 orientation="h" if horizontal else "v", labels={"health_status": "", "projects": "Projects"})
    fig.update_traces(marker_line=dict(color="white", width=1.5))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None)
    if not horizontal:
        fig.update_yaxes(title="Projects", dtick=2)
    else:
        fig.update_xaxes(showgrid=True, gridcolor=COLORS["Grid"], dtick=2)
        fig.update_yaxes(showgrid=False)
    return _style(fig, 330)


def schedule_performance(p, top_n=12):
    """Planned vs actual completion for active projects with the largest gap."""
    a = p[p.is_active] if not _empty(p) else p
    if _empty(a):
        return None
    a = a.sort_values("progress_gap", ascending=False).head(top_n).sort_values("progress_gap")
    lbl = a.project_id + " " + a.region
    fig = go.Figure()
    fig.add_bar(y=lbl, x=a.planned_completion_percentage, orientation="h", name="Planned %", marker_color=SERIES["Planned"],
                hovertemplate="%{y}<br>Planned: %{x:.0f}%<extra></extra>")
    fig.add_bar(y=lbl, x=a.completion_percentage, orientation="h", name="Actual %", marker_color=SERIES["Actual"],
                hovertemplate="%{y}<br>Actual: %{x:.0f}%<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3)
    fig.update_xaxes(range=[0, 100], ticksuffix="%", showgrid=True, gridcolor=COLORS["Grid"])
    fig.update_yaxes(showgrid=False)
    return _style(fig, 400)


def budget_performance(p, by="client"):
    if _empty(p):
        return None
    g = p.groupby(by)[["budget", "budget_spent", "forecast_cost"]].sum() / 1e6
    g = g.rename(columns={"budget": "Budget", "budget_spent": "Actual Spend", "forecast_cost": "Forecast Cost"})
    g = g.sort_values("Budget", ascending=False)
    fig = go.Figure()
    for col in g.columns:
        fig.add_bar(x=g.index, y=g[col], name=col, marker_color=SERIES[col],
                    hovertemplate="%{x}<br>" + col + ": SAR %{y:.1f}M<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3)
    fig.update_yaxes(title="SAR M")
    return _style(fig, 340)


def progress_line(fin, project_row):
    if _empty(fin):
        return None
    fig = go.Figure()
    fig.add_scatter(x=fin.period_end, y=fin.planned_progress_pct, name="Planned", mode="lines",
                    line=dict(color=SERIES["Planned"], width=2, dash="dash"),
                    hovertemplate="%{x|%d %b %Y}<br>Planned: %{y:.0f}%<extra></extra>")
    fig.add_scatter(x=fin.period_end, y=fin.actual_progress_pct, name="Actual", mode="lines",
                    line=dict(color=SERIES["Actual"], width=2.5),
                    hovertemplate="%{x|%d %b %Y}<br>Actual: %{y:.0f}%<extra></extra>")
    fig.update_yaxes(range=[0, 102], ticksuffix="%", title="Cumulative progress")
    return _style(fig, 330)


def cost_curve(fin, project_row):
    if _empty(fin):
        return None
    fig = go.Figure()
    fig.add_scatter(x=fin.period_end, y=fin.planned_cum_cost / 1e6, name="Planned spend", mode="lines",
                    line=dict(color=SERIES["Planned"], width=2, dash="dash"),
                    hovertemplate="%{x|%d %b %Y}<br>Planned: SAR %{y:.1f}M<extra></extra>")
    fig.add_scatter(x=fin.period_end, y=fin.actual_cum_cost / 1e6, name="Actual spend", mode="lines",
                    line=dict(color=SERIES["Actual"], width=2.5),
                    hovertemplate="%{x|%d %b %Y}<br>Actual: SAR %{y:.1f}M<extra></extra>")
    fig.add_hline(y=project_row["forecast_cost"] / 1e6, line=dict(color=SERIES["Forecast Cost"], width=1.5, dash="dot"),
                  annotation_text="Forecast cost at completion", annotation_position="top left",
                  annotation_font=dict(size=11, color=COLORS["Muted"]))
    fig.update_yaxes(title="Cumulative SAR M")
    return _style(fig, 330)


def project_cost_bars(row):
    vals = {"Budget": row["budget"], "Actual Spend": row["budget_spent"], "Forecast Cost": row["forecast_cost"]}
    fig = go.Figure(go.Bar(x=list(vals), y=[v / 1e6 for v in vals.values()], marker_color=[SERIES[k] for k in vals],
                           text=[f"{v / 1e6:.1f}M" for v in vals.values()], textposition="outside",
                           hovertemplate="%{x}: SAR %{y:.2f}M<extra></extra>"))
    fig.update_yaxes(title="SAR M", rangemode="tozero")
    fig.update_layout(bargap=0.5)
    return _style(fig, 330, legend=False)


def count_bar(df, col, color_map=None, order=None, horizontal=True, title=None):
    if _empty(df):
        return None
    c = df[col].value_counts()
    if order:
        c = c.reindex([o for o in order if o in c.index])
    else:
        c = c.sort_values()
    colors = [color_map.get(k, COLORS["Info"]) for k in c.index] if color_map else COLORS["Info"]
    fig = go.Figure(go.Bar(x=c.values if horizontal else c.index, y=c.index if horizontal else c.values,
                           orientation="h" if horizontal else "v", marker_color=colors,
                           text=c.values, textposition="outside",
                           hovertemplate="%{y}: %{x}<extra></extra>" if horizontal else "%{x}: %{y}<extra></extra>"))
    fig.update_layout(bargap=0.4)
    if horizontal:
        fig.update_xaxes(showgrid=False, visible=False)
        fig.update_yaxes(showgrid=False, autorange="reversed" if order else True)
    else:
        fig.update_yaxes(title="Items")
    return _style(fig, 300, legend=False, title=title)


def variance_hist(p):
    a = p[p.is_active] if not _empty(p) else p
    if _empty(a):
        return None
    fig = px.histogram(a, x="schedule_variance_days", nbins=14, color_discrete_sequence=[COLORS["Info"]])
    fig.update_traces(marker_line=dict(color="white", width=1.5),
                      hovertemplate="%{x} days behind: %{y} projects<extra></extra>")
    fig.add_vline(x=0, line=dict(color=COLORS["Muted"], width=1))
    fig.update_xaxes(title="Schedule variance (days behind plan; negative = ahead)")
    fig.update_yaxes(title="Projects")
    return _style(fig, 320, legend=False)


def milestone_status_bar(m):
    if _empty(m):
        return None
    t = m.groupby("status").size().reindex(["Completed", "On Track", "At Risk", "Delayed"]).dropna()
    fig = go.Figure(go.Bar(x=t.index, y=t.values, marker_color=[MILESTONE_COLORS[k] for k in t.index],
                           text=t.values.astype(int), textposition="outside",
                           hovertemplate="%{x}: %{y} milestones<extra></extra>"))
    fig.update_layout(bargap=0.45)
    fig.update_yaxes(title="Milestones")
    return _style(fig, 320, legend=False)


def gantt(p, max_rows=25):
    a = p[p.is_active] if not _empty(p) else p
    if _empty(a):
        return None
    a = a.sort_values("attention_score", ascending=False).head(max_rows).sort_values("planned_start", ascending=False)
    label = a.project_id + " · " + a.region
    fig = go.Figure()
    for status in ["On Track", "At Risk", "Critical"]:
        s = a[a.health_status == status]
        if s.empty:
            continue
        lbl = s.project_id + " · " + s.region
        fig.add_bar(y=lbl, base=s.planned_start, x=(s.planned_end - s.planned_start).dt.total_seconds() * 1000,
                    orientation="h", name=status, marker_color=COLORS[status], width=0.55,
                    customdata=s[["project_name", "completion_percentage", "schedule_variance_days"]].assign(
                        ps=s.planned_start.dt.strftime("%d %b %Y"), pe=s.planned_end.dt.strftime("%d %b %Y"),
                        fe=s.forecast_end.dt.strftime("%d %b %Y")).values,
                    hovertemplate="<b>%{customdata[0]}</b><br>Start: %{customdata[3]}<br>Planned end: %{customdata[4]}"
                                  "<br>Forecast end: %{customdata[5]}<br>Progress: %{customdata[1]:.0f}%"
                                  "<br>Variance: %{customdata[2]} days<extra>" + status + "</extra>")
    slip = a[a.forecast_end > a.planned_end]
    if not slip.empty:
        fig.add_bar(y=slip.project_id + " · " + slip.region, base=slip.planned_end,
                    x=(slip.forecast_end - slip.planned_end).dt.total_seconds() * 1000, orientation="h",
                    name="Forecast slip", marker=dict(color="rgba(200,72,58,0.25)", line=dict(color=COLORS["Critical"], width=1)),
                    width=0.55, hovertemplate="Forecast slip: %{customdata} days<extra></extra>",
                    customdata=slip.schedule_variance_days)
    fig.add_vline(x=pd.Timestamp(AS_OF), line=dict(color=COLORS["Ink"], width=1.5, dash="dot"))
    fig.add_annotation(x=pd.Timestamp(AS_OF), y=1.0, yref="paper", text="Today", showarrow=False, yanchor="bottom",
                       font=dict(size=11, color=COLORS["Ink"]))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(type="date", showgrid=True, gridcolor=COLORS["Grid"])
    fig.update_yaxes(showgrid=False)
    return _style(fig, max(380, 24 * len(a) + 90))


def budget_by_project(p, top_n=15):
    if _empty(p):
        return None
    a = p.copy()
    a["over"] = a.forecast_cost - a.budget
    a = a.sort_values("budget", ascending=False).head(top_n)
    fig = go.Figure()
    fig.add_bar(x=a.project_id, y=a.budget / 1e6, name="Budget", marker_color=SERIES["Budget"],
                hovertemplate="%{x}<br>Budget: SAR %{y:.1f}M<extra></extra>")
    fig.add_bar(x=a.project_id, y=a.budget_spent / 1e6, name="Actual Spend", marker_color=SERIES["Actual Spend"],
                hovertemplate="%{x}<br>Spend: SAR %{y:.1f}M<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.3)
    fig.update_yaxes(title="SAR M")
    return _style(fig, 340)


def utilization_by_client(p):
    if _empty(p):
        return None
    g = p.groupby("client")[["budget", "budget_spent"]].sum()
    g["u"] = g.budget_spent / g.budget * 100
    g = g.sort_values("u")
    fig = go.Figure(go.Bar(x=g.u, y=g.index, orientation="h", marker_color=COLORS["Info"],
                           text=[f"{v:.0f}%" for v in g.u], textposition="outside",
                           hovertemplate="%{y}: %{x:.0f}% of budget spent<extra></extra>"))
    fig.update_xaxes(range=[0, 110], ticksuffix="%", showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.45)
    return _style(fig, 300, legend=False)


def forecast_vs_budget(p):
    if _empty(p):
        return None
    a = p.assign(state=lambda d: (d.forecast_cost > d.budget).map({True: "Forecast over budget", False: "Within budget"}))
    mx = max(a.budget.max(), a.forecast_cost.max()) / 1e6 * 1.05
    fig = px.scatter(a, x=a.budget / 1e6, y=a.forecast_cost / 1e6, color="state",
                     color_discrete_map={"Forecast over budget": COLORS["Critical"], "Within budget": COLORS["Info"]},
                     hover_name="project_id", hover_data={"project_name": True}, labels={"x": "Budget (SAR M)", "y": "Forecast cost (SAR M)", "state": ""})
    fig.update_traces(marker=dict(size=10, line=dict(color="white", width=2)))
    fig.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx, line=dict(color=COLORS["Muted"], width=1, dash="dot"))
    fig.update_xaxes(range=[0, mx], showgrid=True, gridcolor=COLORS["Grid"])
    fig.update_yaxes(range=[0, mx])
    return _style(fig, 340)


def overrun_bars(p, top_n=12):
    o = p[p.forecast_cost > p.budget] if not _empty(p) else p
    if _empty(o):
        return None
    o = o.assign(over=(o.forecast_cost - o.budget) / 1e6).sort_values("over", ascending=False).head(top_n).sort_values("over")
    fig = go.Figure(go.Bar(x=o.over, y=o.project_id + " · " + o.region, orientation="h", marker_color=COLORS["Critical"],
                           text=[f"{v:.1f}M ({pc:.0%})" for v, pc in zip(o.over, o.cost_overrun_pct)], textposition="outside",
                           hovertemplate="%{y}<br>Exposure: SAR %{x:.2f}M<extra></extra>"))
    fig.update_xaxes(visible=False, showgrid=False, range=[0, o.over.max() * 1.35])
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.4)
    return _style(fig, 340, legend=False)
