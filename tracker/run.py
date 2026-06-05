import threading
from typing import Optional

from . import utils
from .store import SQLiteStore


class Run:
    """
    Represents a single experiment run. Use as a context manager (preferred)
    or call end() explicitly.

        with Run(store, name="regime-v2", tags={"universe": "US_equities"}) as run:
            run.log_params({"lookback": 60, "threshold": 0.65})
            run.log_metric("sharpe", 1.42)
    """

    def __init__(self, store: SQLiteStore, name: str = "", tags: dict = None):
        self._store = store
        self.run_id = utils.generate_run_id()
        self.name = name or f"run-{self.run_id[:8]}"
        self.tags = tags or {}
        self.status = "running"
        self.start_time = utils.now_iso()
        self.end_time: Optional[str] = None
        self._step_counters: dict[str, int] = {}
        self._lock = threading.Lock()

        self._store.create_run(
            run_id=self.run_id,
            name=self.name,
            tags=self.tags,
            start_time=self.start_time,
        )

    # --- Context manager ---

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.end(status="failed" if exc_type is not None else "completed")
        return False  # never suppress the caller's exception

    # --- Logging ---

    def log_param(self, key: str, value) -> None:
        self._store.log_param(self.run_id, key, value)

    def log_params(self, params: dict) -> None:
        for k, v in params.items():
            self.log_param(k, v)

    def log_metric(self, key: str, value: float, step: int = None) -> None:
        with self._lock:
            if step is None:
                step = self._step_counters.get(key, 0)
                self._step_counters[key] = step + 1
            else:
                self._step_counters[key] = max(self._step_counters.get(key, 0), step + 1)
        self._store.log_metric(self.run_id, key, float(value), step)

    def log_artifact(self, local_path: str, name: str = None) -> dict:
        return self._store.log_artifact(self.run_id, local_path, name)

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value
        self._store.update_run_tags(self.run_id, self.tags)

    # --- Finalisation ---

    def end(self, status: str = "completed") -> None:
        self.status = status
        self.end_time = utils.now_iso()
        self._store.update_run_status(self.run_id, status, self.end_time)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "status": self.status,
            "tags": self.tags,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    def __repr__(self) -> str:
        return f"<Run id={self.run_id[:8]} name={self.name!r} status={self.status}>"
