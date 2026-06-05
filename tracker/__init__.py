"""
horizonx-tracker public API

Fluent style:
    import tracker
    tracker.start_run("regime-v2", tags={"universe": "US_equities"})
    tracker.log_param("lookback", 60)
    tracker.log_metric("sharpe", 1.42)
    tracker.end_run()

Context manager style (preferred):
    with tracker.start_run("regime-v2") as run:
        run.log_param("lookback", 60)
        run.log_metric("sharpe", 1.42)
"""
from __future__ import annotations

from typing import Optional

from .store import JSONExporter, SQLiteStore
from .run import Run

__all__ = [
    "start_run", "log_param", "log_metric",
    "log_artifact", "end_run", "get_run", "list_runs",
    "Run", "SQLiteStore", "JSONExporter",
]

_active_run: Optional[Run] = None
_store: Optional[SQLiteStore] = None


def _require_active_run() -> Run:
    if _active_run is None:
        raise RuntimeError("No active run. Call tracker.start_run() first.")
    return _active_run


def start_run(
    name: str = "",
    tags: dict = None,
    db_path: str = "tracker.db",
) -> Run:
    global _active_run, _store
    _store = SQLiteStore(db_path=db_path)
    _active_run = Run(_store, name=name, tags=tags or {})
    return _active_run


def log_param(key: str, value) -> None:
    _require_active_run().log_param(key, value)


def log_metric(key: str, value: float, step: int = None) -> None:
    _require_active_run().log_metric(key, value, step)


def log_artifact(local_path: str, name: str = None) -> dict:
    return _require_active_run().log_artifact(local_path, name)


def end_run(status: str = "completed") -> None:
    global _active_run
    _require_active_run().end(status=status)
    _active_run = None


# --- Query API (stateless) ---

def get_run(run_id: str, db_path: str = "tracker.db") -> dict:
    store = SQLiteStore(db_path=db_path)
    run = store.get_run(run_id)
    if run is None:
        raise KeyError(f"Run {run_id!r} not found in {db_path!r}")
    run["params"] = store.get_params(run_id)
    run["metrics"] = store.get_metrics(run_id)
    run["artifacts"] = store.get_artifacts(run_id)
    return run


def list_runs(
    db_path: str = "tracker.db",
    status: str = None,
    tag: str = None,
) -> list[dict]:
    return SQLiteStore(db_path=db_path).list_runs(status=status, tag=tag)
