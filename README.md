# HorizonX Tracker

A lightweight ML experiment tracking library built from scratch in Python. Logs hyperparameters, metrics, and artifacts from model training runs to a local SQLite database, with a Streamlit dashboard for interactive analysis and run comparison.

Built as the experiment logging backend for a macro regime classification trading strategy.

---

## Features

- **Run tracking** — every experiment is recorded with a unique ID, status (`running` / `completed` / `failed`), timestamps, and tags
- **Hyperparameter logging** — log any key-value config; idempotent re-logging matches MLflow behaviour
- **Metric logging** — scalar metrics with optional step index; auto-increments steps when not provided; thread-safe
- **Artifact storage** — files are physically copied into versioned storage; original and stored paths both recorded
- **JSON export** — export any run or the full history to JSON for downstream analysis
- **Streamlit dashboard** — three-page UI: run list with filtering, run detail with charts, and run comparison
- **Smart chart routing** — single-value metrics render as bar charts; time-series metrics render as line charts
- **Fluent API** — MLflow-style module-level functions (`start_run`, `log_metric`, …) plus context manager support

---

## Tech Stack

| Layer | Technology |
|---|---|
| Storage | SQLite with WAL mode (concurrent read/write) |
| Data access | Python `sqlite3` stdlib — zero ORM overhead |
| Dashboard | Streamlit + Plotly |
| Packaging | `pip install -e .` (editable install) |
| Testing | pytest |
| CI | GitHub Actions (Python 3.10 / 3.11 / 3.12) |

---

## Installation

```bash
git clone https://github.com/your-username/horizonx-tracker
cd horizonx-tracker
pip install -e ".[dev]"
```

---

## Quick Start

**Context manager style (recommended):**

```python
import tracker

with tracker.start_run("regime-expansion", tags={"universe": "US_equities"}) as run:
    run.log_params({
        "lookback":       60,
        "threshold":      0.65,
        "rebalance_freq": "monthly",
    })

    for month, result in enumerate(backtest_results):
        run.log_metric("equity_curve",   result.equity,  step=month)
        run.log_metric("monthly_return", result.ret,     step=month)
        run.log_metric("sharpe",         result.sharpe,  step=month)

    run.log_metric("annualised_return", results.ann_return)
    run.log_metric("max_drawdown",      results.max_dd)
    run.log_artifact("models/regime_classifier.pkl")
```

Status is automatically set to `completed` on exit, or `failed` if an exception is raised.

**Fluent style:**

```python
import tracker

tracker.start_run("regime-v2", db_path="experiments.db")
tracker.log_param("lookback", 120)
tracker.log_metric("sharpe", 1.42)
tracker.end_run()
```

**Querying runs:**

```python
runs = tracker.list_runs(status="completed", tag="regime")
run  = tracker.get_run(run_id)   # includes params, metrics, artifacts
```

**JSON export:**

```python
from tracker.store import SQLiteStore, JSONExporter

store    = SQLiteStore("tracker.db")
exporter = JSONExporter(store)
print(exporter.to_json())          # all runs
print(exporter.to_json(run_id))    # single run
```

---

## Dashboard

```bash
streamlit run dashboard/app.py
# or point at a specific database:
streamlit run dashboard/app.py -- --db /path/to/experiments.db
```

**Run List** — filterable table of all experiments with status, tags, and timestamps

**Run Detail** — hyperparameter table, summary metric bar chart, time-series line chart, artifact log

**Run Comparison** — grouped bar chart comparing summary metrics across selected runs; overlaid line chart for time-series metrics

---

## Running Tests

```bash
pytest tests/ -v
```

20 tests covering run lifecycle, param/metric/artifact logging, SQLite persistence, JSON export, and the fluent API.

---

## Project Structure

```
horizonx-tracker/
├── tracker/
│   ├── __init__.py     # Public API — start_run, log_param, log_metric, …
│   ├── run.py          # Run class with context manager and thread-safe step counters
│   ├── store.py        # SQLiteStore and JSONExporter
│   └── utils.py        # UUID generation, timestamps, artifact file I/O
├── dashboard/
│   └── app.py          # Streamlit dashboard (three pages)
├── examples/
│   └── demo.py         # Simulated regime classifier backtest demo
├── tests/
│   └── test_tracker.py
├── .github/workflows/
│   └── ci.yml
└── setup.py
```

---

## Design Notes

**Why SQLite over a hosted DB?** The tracker is designed to run locally alongside a research codebase. SQLite with WAL mode supports concurrent reads from the dashboard while a training script is writing — no server required.

**Why copy artifacts instead of storing paths?** Path-only storage breaks when source files are in `/tmp` or get deleted. Copying gives the tracker ownership of the data.

**Why no step uniqueness constraint on metrics?** Logging the same metric key at multiple steps is the intended use case (monthly returns, rolling Sharpe). Only params enforce uniqueness — re-logging the same param is idempotent by design.
