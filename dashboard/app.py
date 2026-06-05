"""
HorizonX Experiment Tracker Dashboard
Run:  streamlit run dashboard/app.py [-- --db tracker.db]
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tracker.store import SQLiteStore

# ── Design tokens ──────────────────────────────────────────────────────────

BG       = "#0b0f1a"
SURFACE  = "#111827"
SURFACE2 = "#1f2937"
BORDER   = "#2d3748"
ACCENT   = "#10b981"   # Emerald — professional, readable
ACCENT_L = "#34d399"
TEXT     = "#f3f4f6"
TEXT_DIM = "#9ca3af"
RED      = "#ef4444"
ORANGE   = "#f59e0b"
BLUE     = "#6366f1"
PURPLE   = "#a855f7"

_STATUS_COLOUR = {"running": ORANGE, "completed": ACCENT, "failed": RED}
_CHART_COLORS  = [ACCENT, BLUE, ORANGE, PURPLE, RED, ACCENT_L]

_PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=BG,
    font=dict(color=TEXT, family="Inter, system-ui, sans-serif", size=12),
    xaxis=dict(
        gridcolor=BORDER,
        zerolinecolor=BORDER,
        tickfont=dict(color=TEXT_DIM, family="'JetBrains Mono', monospace"),
        title_font=dict(color=TEXT_DIM),
    ),
    yaxis=dict(
        gridcolor=BORDER,
        zerolinecolor=BORDER,
        tickfont=dict(color=TEXT_DIM, family="'JetBrains Mono', monospace"),
        title_font=dict(color=TEXT_DIM),
    ),
    colorway=_CHART_COLORS,
    legend=dict(
        bgcolor=SURFACE2, bordercolor=BORDER, borderwidth=1,
        font=dict(color=TEXT, family="Inter, sans-serif"),
    ),
    hoverlabel=dict(
        bgcolor=SURFACE2, bordercolor=BORDER,
        font=dict(color=TEXT, family="'JetBrains Mono', monospace"),
    ),
    margin=dict(l=50, r=28, t=44, b=44),
)

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Base ──────────────────────────────────────────────────── */
html, body, [data-testid="stApp"] {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
}}
.main .block-container {{
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}}

/* ── Sidebar ───────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {SURFACE};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebarContent"] {{ padding: 2rem 1.25rem; }}

/* ── Typography ────────────────────────────────────────────── */
h1, h2, h3, h4 {{
    color: {TEXT};
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    letter-spacing: -0.02em;
}}
h2 {{
    font-size: 1.375rem;
    border-bottom: 1px solid {BORDER};
    padding-bottom: 0.875rem;
    margin-bottom: 1.75rem;
}}
hr {{ border-color: {BORDER} !important; margin: 1.5rem 0 !important; }}
[data-testid="stCaptionContainer"] p {{
    color: {TEXT_DIM} !important;
    font-size: 0.78rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

/* ── Inputs / Selects ──────────────────────────────────────── */
[data-baseweb="select"] > div,
[data-testid="stSelectbox"] > div > div {{
    background-color: {SURFACE2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
    font-size: 0.875rem !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
[data-baseweb="select"]:focus-within > div {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT}20 !important;
}}
[data-baseweb="input"] {{
    background-color: {SURFACE2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
    font-size: 0.875rem !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
[data-baseweb="input"]:focus-within {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT}20 !important;
}}
input {{
    background-color: {SURFACE2} !important;
    color: {TEXT} !important;
    caret-color: {ACCENT} !important;
    font-family: 'Inter', sans-serif !important;
}}
label, [data-testid="stWidgetLabel"] p {{
    color: {TEXT_DIM} !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-family: 'Inter', sans-serif !important;
}}
::placeholder {{ color: {BORDER} !important; }}

/* ── Multiselect tags ──────────────────────────────────────── */
[data-baseweb="tag"] {{
    background-color: {ACCENT}15 !important;
    border: 1px solid {ACCENT}35 !important;
    border-radius: 6px !important;
    color: {ACCENT} !important;
    font-size: 0.78rem !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ── Buttons ───────────────────────────────────────────────── */
[data-testid="baseButton-primary"] {{
    background-color: {ACCENT} !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    letter-spacing: -0.01em;
    transition: background 0.15s, box-shadow 0.15s;
}}
[data-testid="baseButton-primary"]:hover {{
    background-color: {ACCENT_L} !important;
    box-shadow: 0 0 0 3px {ACCENT}30 !important;
}}
[data-testid="baseButton-secondary"] {{
    background-color: transparent !important;
    color: {TEXT_DIM} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    transition: all 0.15s;
}}
[data-testid="baseButton-secondary"]:hover {{
    background-color: {SURFACE2} !important;
    color: {TEXT} !important;
    border-color: {TEXT_DIM} !important;
}}

/* ── Expanders ─────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    margin-bottom: 1rem;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    color: {TEXT} !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 0.875rem 1.25rem !important;
    background-color: {SURFACE} !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stExpander"] summary:hover {{ background-color: {SURFACE2} !important; }}
[data-testid="stExpanderDetails"] {{
    background-color: {SURFACE} !important;
    border-top: 1px solid {BORDER} !important;
    padding: 1.25rem !important;
}}
[data-testid="stExpander"] summary svg {{ color: {TEXT_DIM} !important; }}

/* ── Radio / Nav ───────────────────────────────────────────── */
[data-testid="stRadio"] > div {{ gap: 0.2rem; }}
[data-testid="stRadio"] label {{
    color: {TEXT_DIM} !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    padding: 0.5rem 0.875rem !important;
    border-radius: 8px !important;
    cursor: pointer;
    border: 1px solid transparent !important;
    transition: all 0.12s;
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stRadio"] label:hover {{
    background-color: {SURFACE2} !important;
    color: {TEXT} !important;
}}
[data-testid="stRadio"] [aria-checked="true"] label {{
    background-color: {ACCENT}15 !important;
    color: {ACCENT} !important;
    border-color: {ACCENT}30 !important;
    font-weight: 500 !important;
}}

/* ── Alerts ────────────────────────────────────────────────── */
[data-testid="stAlert"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
}}
[data-testid="stAlert"] p {{
    color: {TEXT_DIM} !important;
    font-size: 0.875rem !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ── Dataframe ─────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
}}
[data-testid="stDataFrame"] iframe {{ border-radius: 10px; }}

/* ── Plotly container ──────────────────────────────────────── */
[data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    background-color: {SURFACE};
}}

/* ── Scrollbar ─────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: {TEXT_DIM}; }}
</style>
"""


# ── HTML component helpers ─────────────────────────────────────────────────

def _pill(status: str) -> str:
    c      = _STATUS_COLOUR.get(status, TEXT_DIM)
    labels = {"running": "Running", "completed": "Completed", "failed": "Failed"}
    label  = labels.get(status, status.capitalize())
    return (
        f"<span style='display:inline-flex;align-items:center;gap:5px;"
        f"background:{c}15;color:{c};border:1px solid {c}30;"
        f"border-radius:6px;padding:3px 10px;font-size:0.78rem;"
        f"font-weight:500;font-family:Inter,sans-serif'>"
        f"<span style='width:6px;height:6px;border-radius:50%;"
        f"background:{c};flex-shrink:0'></span>{label}</span>"
    )


def _stat_card(label: str, value: str, accent: str = BORDER) -> str:
    return (
        f"<div style='background:{SURFACE};border:1px solid {BORDER};"
        f"border-left:3px solid {accent};border-radius:10px;"
        f"padding:1.125rem 1.25rem;height:100%'>"
        f"<div style='color:{TEXT_DIM};font-size:0.78rem;font-weight:500;"
        f"margin-bottom:10px;font-family:Inter,sans-serif'>{label}</div>"
        f"<div style='color:{TEXT};font-size:1.625rem;font-weight:700;"
        f"font-family:JetBrains Mono,monospace;line-height:1'>{value}</div>"
        f"</div>"
    )


def _section_header(title: str, margin_top: str = "2rem") -> str:
    return (
        f"<div style='font-size:0.8rem;font-weight:600;color:{TEXT_DIM};"
        f"margin:{margin_top} 0 0.875rem;font-family:Inter,sans-serif;"
        f"padding-bottom:0.5rem;border-bottom:1px solid {BORDER}'>{title}</div>"
    )


def _run_header_card(run: dict, run_id: str) -> str:
    return (
        f"<div style='background:{SURFACE};border:1px solid {BORDER};"
        f"border-radius:10px;padding:1.375rem 1.5rem;margin-bottom:1.5rem'>"
        f"<div style='display:flex;align-items:flex-start;"
        f"justify-content:space-between;gap:1rem'>"
        f"<div>"
        f"<div style='font-size:1.125rem;font-weight:600;color:{TEXT};"
        f"letter-spacing:-0.02em;margin-bottom:6px;font-family:Inter,sans-serif'>"
        f"{run['name']}</div>"
        f"<div style='font-size:0.78rem;color:{TEXT_DIM};"
        f"font-family:JetBrains Mono,monospace'>"
        f"{run_id} &nbsp;·&nbsp; {run['start_time']} → {run.get('end_time') or '…'}"
        f"</div></div>"
        f"{_pill(run['status'])}"
        f"</div></div>"
    )


def _runs_table(runs: list[dict]) -> str:
    th = (
        f"padding:11px 16px;text-align:left;color:{TEXT_DIM};"
        f"font-size:0.78rem;font-weight:600;white-space:nowrap;"
        f"font-family:Inter,sans-serif;border-bottom:1px solid {BORDER}"
    )
    head = (
        f"<thead><tr style='background:{SURFACE2}'>"
        f"<th style='{th}'>Run ID</th><th style='{th}'>Name</th>"
        f"<th style='{th}'>Status</th><th style='{th}'>Tags</th>"
        f"<th style='{th}'>Started</th><th style='{th}'>Ended</th>"
        f"</tr></thead>"
    )
    body = "<tbody>"
    for r in runs:
        tags = "  ·  ".join(f"{k}: {v}" for k, v in r["tags"].items()) or "—"
        end  = r.get("end_time") or "—"
        td   = (f"padding:12px 16px;border-bottom:1px solid {BORDER};"
                f"font-family:Inter,sans-serif")
        body += (
            f"<tr style='transition:background 0.1s' "
            f"onmouseover=\"this.style.background='{SURFACE2}'\" "
            f"onmouseout=\"this.style.background='transparent'\">"
            f"<td style='{td};color:{TEXT_DIM};font-family:JetBrains Mono,monospace;"
            f"font-size:0.8rem'>{r['run_id'][:8]}</td>"
            f"<td style='{td};color:{TEXT};font-weight:500'>{r['name']}</td>"
            f"<td style='{td}'>{_pill(r['status'])}</td>"
            f"<td style='{td};color:{TEXT_DIM};font-size:0.8rem'>{tags}</td>"
            f"<td style='{td};color:{TEXT_DIM};font-size:0.8rem;"
            f"font-family:JetBrains Mono,monospace'>{r['start_time']}</td>"
            f"<td style='{td};color:{TEXT_DIM};font-size:0.8rem;"
            f"font-family:JetBrains Mono,monospace'>{end}</td>"
            f"</tr>"
        )
    body += "</tbody>"
    return (
        f"<div style='border:1px solid {BORDER};border-radius:10px;"
        f"overflow:hidden;margin-bottom:1.5rem'>"
        f"<table style='width:100%;border-collapse:collapse;background:{SURFACE}'>"
        f"{head}{body}</table></div>"
    )


# ── Store ──────────────────────────────────────────────────────────────────

@st.cache_resource
def get_store(db_path: str) -> SQLiteStore:
    return SQLiteStore(db_path=db_path)


# ── Pages ──────────────────────────────────────────────────────────────────

def page_run_list(store: SQLiteStore) -> None:
    all_runs = store.list_runs()
    n_total  = len(all_runs)
    n_done   = sum(1 for r in all_runs if r["status"] == "completed")
    n_fail   = sum(1 for r in all_runs if r["status"] == "failed")
    n_run    = sum(1 for r in all_runs if r["status"] == "running")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_stat_card("Total Runs",  str(n_total), BORDER),  unsafe_allow_html=True)
    c2.markdown(_stat_card("Completed",   str(n_done),  ACCENT),  unsafe_allow_html=True)
    c3.markdown(_stat_card("Failed",      str(n_fail),  RED),     unsafe_allow_html=True)
    c4.markdown(_stat_card("Running",     str(n_run),   ORANGE),  unsafe_allow_html=True)

    st.markdown(_section_header("Filter runs"), unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    status_filter = col1.selectbox(
        "Status", ["All", "Completed", "Running", "Failed"],
        label_visibility="visible",
    )
    tag_filter = col2.text_input(
        "Tag key", "", placeholder="e.g. regime",
        label_visibility="visible",
    )

    runs = store.list_runs(
        status=None if status_filter == "All" else status_filter.lower(),
        tag=tag_filter or None,
    )

    if not runs:
        st.info("No runs match the current filters.")
        return

    st.markdown(_section_header("Runs"), unsafe_allow_html=True)
    st.markdown(_runs_table(runs), unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 1])
    run_id = col_a.selectbox(
        "Select run",
        [r["run_id"] for r in runs],
        format_func=lambda rid: (
            f"{next(r['name'] for r in runs if r['run_id'] == rid)}  —  {rid[:8]}"
        ),
        label_visibility="visible",
    )
    if col_b.button("Open →", type="primary", use_container_width=True):
        st.session_state["detail_run_id"] = run_id
        st.session_state["page"] = "Run Detail"
        st.rerun()


def page_run_detail(store: SQLiteStore) -> None:
    run_id = st.session_state.get("detail_run_id")
    if not run_id:
        st.info("No run selected. Go to Run List and click Open →")
        return

    run = store.get_run(run_id)
    if run is None:
        st.error(f"Run `{run_id}` not found.")
        return

    params    = store.get_params(run_id)
    metrics   = store.get_metrics(run_id)
    artifacts = store.get_artifacts(run_id)

    st.markdown(_run_header_card(run, run_id), unsafe_allow_html=True)

    # Metric summary cards — single-point metrics only, strategy before benchmark
    if metrics:
        mdf    = pd.DataFrame(metrics)
        counts = mdf.groupby("key")["step"].count()
        last   = mdf.sort_values("step").groupby("key")["value"].last()
        # Only single-point (summary) metrics belong in cards
        summary = [k for k in last.index if counts[k] == 1]
        priority = [k for k in summary if not k.startswith("spy_")]
        fallback = [k for k in summary if k.startswith("spy_")]
        top  = (priority + fallback)[:4]
        cols = st.columns(len(top))
        for i, key in enumerate(top):
            v   = last[key]
            fmt = f"{v:.2%}" if any(t in key for t in ("return", "drawdown")) else f"{v:.4f}"
            cols[i].markdown(
                _stat_card(key.replace("_", " ").title(), fmt, ACCENT),
                unsafe_allow_html=True,
            )

    # Hyperparameters
    st.markdown(_section_header("Hyperparameters"), unsafe_allow_html=True)
    with st.expander("Parameters", expanded=True):
        if params:
            st.dataframe(
                pd.DataFrame(params.items(), columns=["Parameter", "Value"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No parameters logged.")

    # Metrics
    st.markdown(_section_header("Metrics"), unsafe_allow_html=True)
    if not metrics:
        st.info("No metrics logged.")
    else:
        mdf      = pd.DataFrame(metrics)
        all_keys = sorted(mdf["key"].unique())
        counts   = mdf.groupby("key")["step"].count()
        summary_keys = [k for k in all_keys if counts[k] == 1]
        series_keys  = [k for k in all_keys if counts[k] > 1]

        if summary_keys:
            last = mdf[mdf["key"].isin(summary_keys)].groupby("key")["value"].first()
            sel  = st.multiselect(
                "Select metrics to display", summary_keys,
                default=summary_keys, key="detail_summary",
            )
            if sel:
                vals    = [last[k] for k in sel]
                colours = [ACCENT if v >= 0 else RED for v in vals]
                fig = go.Figure(go.Bar(
                    x=vals, y=sel, orientation="h",
                    marker=dict(color=colours, opacity=0.9, line=dict(width=0)),
                    hovertemplate="%{y}: %{x:.4f}<extra></extra>",
                ))
                fig.update_layout(height=max(220, len(sel) * 38 + 80), **_PLOTLY_LAYOUT)
                fig.update_xaxes(title_text="Value")
                fig.update_yaxes(autorange="reversed", zerolinecolor=ACCENT)
                st.plotly_chart(fig, use_container_width=True)

        if series_keys:
            if summary_keys:
                st.markdown(
                    _section_header("Time Series"), unsafe_allow_html=True,
                )
            sel = st.multiselect(
                "Select metrics to plot", series_keys,
                default=series_keys, key="detail_series",
            )
            if sel:
                fig = go.Figure()
                for i, key in enumerate(sel):
                    sub = mdf[mdf["key"] == key].sort_values("step")
                    c   = _CHART_COLORS[i % len(_CHART_COLORS)]
                    fig.add_trace(go.Scatter(
                        x=sub["step"], y=sub["value"],
                        mode="lines", name=key,
                        line=dict(width=1, color=c),
                        hovertemplate=f"<b>{key}</b>  step %{{x}}<br>%{{y:.4f}}<extra></extra>",
                    ))
                fig.update_layout(xaxis_title="Step", yaxis_title="Value",
                                  height=380, **_PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

    # Artifacts
    st.markdown(_section_header("Artifacts"), unsafe_allow_html=True)
    with st.expander("Logged files", expanded=bool(artifacts)):
        if artifacts:
            st.dataframe(
                pd.DataFrame(artifacts)[["name", "stored_path", "size_bytes", "logged_at"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No artifacts logged.")


def page_comparison(store: SQLiteStore) -> None:
    runs = store.list_runs()
    if len(runs) < 2:
        st.warning("Need at least 2 runs to compare.")
        return

    options      = {r["run_id"]: r["name"] for r in runs}
    selected_ids = st.multiselect(
        "Select runs to compare",
        list(options.keys()),
        format_func=lambda rid: options[rid],
        default=list(options.keys())[:2],
    )

    if len(selected_ids) < 2:
        st.info("Select at least 2 runs.")
        return

    # Hyperparameters
    st.markdown(_section_header("Hyperparameters"), unsafe_allow_html=True)
    param_rows: dict = {}
    for rid in selected_ids:
        for k, v in store.get_params(rid).items():
            param_rows.setdefault(k, {})[options[rid]] = v
    if param_rows:
        st.dataframe(
            pd.DataFrame(param_rows).T.rename_axis("Parameter"),
            use_container_width=True,
        )
    else:
        st.info("No parameters logged.")

    # Collect and classify metrics
    all_metrics: dict[str, dict] = {}
    for rid in selected_ids:
        for m in store.get_metrics(rid):
            all_metrics.setdefault(m["key"], {}).setdefault(rid, []).append(m)

    if not all_metrics:
        st.info("No metrics logged for selected runs.")
        return

    step_counts  = {k: max(len(v) for v in by_run.values())
                    for k, by_run in all_metrics.items()}
    summary_keys = sorted(k for k, n in step_counts.items() if n == 1)
    series_keys  = sorted(k for k, n in step_counts.items() if n > 1)

    # Summary metrics — grouped bar chart
    if summary_keys:
        st.markdown(_section_header("Summary Metrics"), unsafe_allow_html=True)
        fig = go.Figure()
        for i, rid in enumerate(selected_ids):
            vals = [
                all_metrics[k][rid][0]["value"] if rid in all_metrics[k] else None
                for k in summary_keys
            ]
            c = _CHART_COLORS[i % len(_CHART_COLORS)]
            fig.add_trace(go.Bar(
                name=options[rid], x=summary_keys, y=vals,
                marker=dict(color=c, opacity=0.85, line=dict(width=0)),
                hovertemplate="%{x}: %{y:.4f}<extra>" + options[rid] + "</extra>",
            ))
        fig.update_layout(barmode="group", height=380, **_PLOTLY_LAYOUT)
        fig.update_xaxes(tickangle=-25)
        fig.update_yaxes(zerolinecolor=ACCENT)
        st.plotly_chart(fig, use_container_width=True)

    # Time series — overlaid line chart
    if series_keys:
        st.markdown(_section_header("Time Series"), unsafe_allow_html=True)
        col1, _ = st.columns([1, 2])
        metric_key = col1.selectbox("Metric", series_keys)
        if metric_key:
            fig = go.Figure()
            for i, rid in enumerate(selected_ids):
                rows = all_metrics[metric_key].get(rid, [])
                if rows:
                    mdf = pd.DataFrame(rows).sort_values("step")
                    c   = _CHART_COLORS[i % len(_CHART_COLORS)]
                    fig.add_trace(go.Scatter(
                        x=mdf["step"], y=mdf["value"],
                        mode="lines", name=options[rid],
                        line=dict(width=1, color=c),
                        hovertemplate=(
                            f"<b>{options[rid]}</b>  step %{{x}}<br>"
                            f"%{{y:.4f}}<extra></extra>"
                        ),
                    ))
            fig.update_layout(
                title=dict(text=metric_key, font=dict(color=TEXT_DIM, size=13)),
                xaxis_title="Step", yaxis_title="Value",
                height=400, **_PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="HorizonX Tracker",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", default="tracker.db")
    args, _ = parser.parse_known_args()
    store = get_store(args.db)

    total_runs = len(store.list_runs())

    with st.sidebar:
        st.markdown(
            f"<div style='margin-bottom:2rem'>"
            f"<div style='font-size:1.125rem;font-weight:700;color:{TEXT};"
            f"letter-spacing:-0.03em;font-family:Inter,sans-serif'>"
            f"HorizonX <span style='color:{ACCENT}'>Tracker</span></div>"
            f"<div style='font-size:0.78rem;color:{TEXT_DIM};margin-top:4px;"
            f"font-family:Inter,sans-serif'>Experiment Platform</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='background:{SURFACE2};border:1px solid {BORDER};"
            f"border-radius:8px;padding:0.75rem 1rem;margin-bottom:1.5rem;"
            f"display:flex;justify-content:space-between;align-items:center'>"
            f"<span style='font-size:0.8rem;color:{TEXT_DIM};"
            f"font-family:Inter,sans-serif'>Total experiments</span>"
            f"<span style='font-size:1rem;font-weight:700;color:{TEXT};"
            f"font-family:JetBrains Mono,monospace'>{total_runs}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        page = st.radio(
            "Navigation",
            ["Run List", "Run Detail", "Run Comparison"],
            index=["Run List", "Run Detail", "Run Comparison"].index(
                st.session_state.get("page", "Run List")
            ),
            label_visibility="collapsed",
        )
        st.session_state["page"] = page
        st.markdown("---")
        if st.button("Refresh", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()
        st.markdown(
            f"<div style='margin-top:1.5rem;color:{BORDER};font-size:0.7rem;"
            f"font-family:JetBrains Mono,monospace;word-break:break-all'>{args.db}</div>",
            unsafe_allow_html=True,
        )

    _titles = {
        "Run List": "Experiment Runs",
        "Run Detail": "Run Detail",
        "Run Comparison": "Run Comparison",
    }
    st.markdown(f"## {_titles[page]}")

    if page == "Run List":
        page_run_list(store)
    elif page == "Run Detail":
        page_run_detail(store)
    elif page == "Run Comparison":
        page_comparison(store)


if __name__ == "__main__":
    main()
