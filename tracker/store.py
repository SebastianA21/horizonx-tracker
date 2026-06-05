import json
import pathlib
import sqlite3
from typing import Optional

from . import utils

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id     TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'running',
    tags       TEXT NOT NULL DEFAULT '{}',
    start_time TEXT NOT NULL,
    end_time   TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS params (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key    TEXT NOT NULL,
    value  TEXT NOT NULL,
    UNIQUE(run_id, key)
);

CREATE TABLE IF NOT EXISTS metrics (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id    TEXT    NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key       TEXT    NOT NULL,
    value     REAL    NOT NULL,
    step      INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_run_key ON metrics(run_id, key);

CREATE TABLE IF NOT EXISTS artifacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    source_path TEXT    NOT NULL,
    stored_path TEXT    NOT NULL,
    size_bytes  INTEGER,
    logged_at   TEXT    NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, db_path: str = "tracker.db", base_dir: str = None):
        self.db_path = str(pathlib.Path(db_path).resolve())
        self.base_dir = base_dir or str(pathlib.Path(db_path).resolve().parent)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # --- Runs ---

    def create_run(self, run_id: str, name: str, tags: dict, start_time: str) -> None:
        sql = """INSERT INTO runs (run_id, name, status, tags, start_time, created_at)
                 VALUES (?, ?, 'running', ?, ?, ?)"""
        with self._connect() as conn:
            conn.execute(sql, (run_id, name, json.dumps(tags), start_time, utils.now_iso()))

    def update_run_status(self, run_id: str, status: str, end_time: str = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status=?, end_time=? WHERE run_id=?",
                (status, end_time, run_id),
            )

    def update_run_tags(self, run_id: str, tags: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET tags=? WHERE run_id=?",
                (json.dumps(tags), run_id),
            )

    def get_run(self, run_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["tags"] = json.loads(result.get("tags", "{}"))
        return result

    def list_runs(self, status: str = None, tag: str = None) -> list[dict]:
        sql = "SELECT * FROM runs"
        params = []
        conditions = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if tag:
            conditions.append("json_extract(tags, '$.' || ?) IS NOT NULL")
            params.append(tag)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags", "{}"))
            result.append(d)
        return result

    # --- Params ---

    def log_param(self, run_id: str, key: str, value) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO params (run_id, key, value) VALUES (?, ?, ?)",
                (run_id, key, str(value)),
            )

    def get_params(self, run_id: str) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM params WHERE run_id=?", (run_id,)
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}

    # --- Metrics ---

    def log_metric(self, run_id: str, key: str, value: float, step: int = 0) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO metrics (run_id, key, value, step, timestamp) VALUES (?, ?, ?, ?, ?)",
                (run_id, key, float(value), step, utils.now_iso()),
            )

    def get_metrics(self, run_id: str, key: str = None) -> list[dict]:
        if key:
            sql = "SELECT key, value, step, timestamp FROM metrics WHERE run_id=? AND key=? ORDER BY step"
            params = (run_id, key)
        else:
            sql = "SELECT key, value, step, timestamp FROM metrics WHERE run_id=? ORDER BY key, step"
            params = (run_id,)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # --- Artifacts ---

    def log_artifact(self, run_id: str, source_path: str, name: str = None) -> dict:
        dest_dir = utils.safe_artifact_dir(self.base_dir, run_id)
        stored_path, size = utils.copy_artifact(source_path, dest_dir, name)
        final_name = name or pathlib.Path(source_path).name
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO artifacts (run_id, name, source_path, stored_path, size_bytes, logged_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, final_name, source_path, stored_path, size, utils.now_iso()),
            )
        return {"name": final_name, "stored_path": stored_path, "size_bytes": size}

    def get_artifacts(self, run_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, source_path, stored_path, size_bytes, logged_at FROM artifacts WHERE run_id=?",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]


class JSONExporter:
    def __init__(self, store: SQLiteStore):
        self._store = store

    def export_run(self, run_id: str) -> dict:
        run = self._store.get_run(run_id)
        if run is None:
            raise ValueError(f"Run {run_id!r} not found")
        run["params"] = self._store.get_params(run_id)
        run["metrics"] = self._store.get_metrics(run_id)
        run["artifacts"] = self._store.get_artifacts(run_id)
        return run

    def export_all(self) -> list[dict]:
        return [self.export_run(r["run_id"]) for r in self._store.list_runs()]

    def to_json(self, run_id: str = None, indent: int = 2) -> str:
        if run_id:
            return json.dumps(self.export_run(run_id), indent=indent)
        return json.dumps(self.export_all(), indent=indent)
