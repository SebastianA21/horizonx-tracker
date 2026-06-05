import json
import pathlib
import pytest

import tracker
from tracker.store import JSONExporter, SQLiteStore
from tracker.run import Run


@pytest.fixture
def tmp_db(tmp_path):
    return SQLiteStore(db_path=str(tmp_path / "test.db"), base_dir=str(tmp_path))


@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test.db")


# --- Run creation ---

class TestRunCreation:
    def test_run_has_run_id(self, tmp_db):
        run = Run(tmp_db, name="test")
        assert len(run.run_id) == 32
        run.end()

    def test_initial_status_is_running(self, tmp_db):
        run = Run(tmp_db, name="r1")
        assert run.status == "running"
        assert tmp_db.get_run(run.run_id)["status"] == "running"
        run.end()

    def test_default_name(self, tmp_db):
        run = Run(tmp_db)
        assert run.name.startswith("run-")
        run.end()

    def test_context_manager_completes(self, tmp_db):
        with Run(tmp_db, name="ctx") as run:
            rid = run.run_id
        stored = tmp_db.get_run(rid)
        assert stored["status"] == "completed"
        assert stored["end_time"] is not None

    def test_context_manager_marks_failed_on_exception(self, tmp_db):
        with pytest.raises(ValueError):
            with Run(tmp_db, name="fail") as run:
                rid = run.run_id
                raise ValueError("boom")
        assert tmp_db.get_run(rid)["status"] == "failed"


# --- Params ---

class TestParams:
    def test_log_param(self, tmp_db):
        with Run(tmp_db, name="p1") as run:
            run.log_param("lr", 0.01)
        assert tmp_db.get_params(run.run_id)["lr"] == "0.01"

    def test_log_params_dict(self, tmp_db):
        with Run(tmp_db, name="p2") as run:
            run.log_params({"lr": 0.01, "epochs": 100})
        assert set(tmp_db.get_params(run.run_id).keys()) == {"lr", "epochs"}

    def test_param_idempotent(self, tmp_db):
        with Run(tmp_db, name="p3") as run:
            run.log_param("lr", 0.01)
            run.log_param("lr", 0.01)
        assert tmp_db.get_params(run.run_id)["lr"] == "0.01"


# --- Metrics ---

class TestMetrics:
    def test_auto_step_increments(self, tmp_db):
        with Run(tmp_db, name="m1") as run:
            for i in range(3):
                run.log_metric("loss", float(3 - i))
        steps = [m["step"] for m in tmp_db.get_metrics(run.run_id, key="loss")]
        assert steps == [0, 1, 2]

    def test_explicit_step(self, tmp_db):
        with Run(tmp_db, name="m2") as run:
            run.log_metric("sharpe", 1.42, step=5)
        assert tmp_db.get_metrics(run.run_id, key="sharpe")[0]["step"] == 5

    def test_multiple_keys(self, tmp_db):
        with Run(tmp_db, name="m3") as run:
            run.log_metric("loss", 1.0)
            run.log_metric("sharpe", 1.5)
        keys = {m["key"] for m in tmp_db.get_metrics(run.run_id)}
        assert keys == {"loss", "sharpe"}


# --- Persistence ---

class TestPersistence:
    def test_run_survives_new_store(self, tmp_path):
        db = str(tmp_path / "p.db")
        s1 = SQLiteStore(db_path=db, base_dir=str(tmp_path))
        with Run(s1, name="persist") as run:
            run.log_param("x", 42)
            rid = run.run_id

        s2 = SQLiteStore(db_path=db, base_dir=str(tmp_path))
        assert s2.get_run(rid)["status"] == "completed"
        assert s2.get_params(rid)["x"] == "42"

    def test_list_runs_all(self, tmp_db):
        for name in ["a", "b", "c"]:
            with Run(tmp_db, name=name):
                pass
        assert len(tmp_db.list_runs()) == 3

    def test_list_runs_filter_status(self, tmp_db):
        with Run(tmp_db, name="ok"):
            pass
        with pytest.raises(RuntimeError):
            with Run(tmp_db, name="bad") as run:
                raise RuntimeError("fail")
        assert len(tmp_db.list_runs(status="completed")) == 1
        assert len(tmp_db.list_runs(status="failed")) == 1


# --- Artifacts ---

class TestArtifacts:
    def test_copies_file(self, tmp_db, tmp_path):
        src = tmp_path / "weights.txt"
        src.write_text("model weights")
        with Run(tmp_db, name="art") as run:
            result = run.log_artifact(str(src))
        assert pathlib.Path(result["stored_path"]).exists()
        assert tmp_db.get_artifacts(run.run_id)[0]["name"] == "weights.txt"

    def test_missing_file_raises(self, tmp_db):
        with pytest.raises(FileNotFoundError):
            with Run(tmp_db, name="bad") as run:
                run.log_artifact("/nonexistent/file.txt")


# --- JSON export ---

class TestJSONExporter:
    def test_export_run(self, tmp_db):
        with Run(tmp_db, name="exp") as run:
            run.log_param("lr", 0.1)
            run.log_metric("loss", 0.5)
            rid = run.run_id
        data = JSONExporter(tmp_db).export_run(rid)
        assert data["params"]["lr"] == "0.1"
        assert len(data["metrics"]) == 1

    def test_to_json_valid(self, tmp_db):
        with Run(tmp_db, name="j"):
            pass
        raw = JSONExporter(tmp_db).to_json()
        assert isinstance(json.loads(raw), list)


# --- Fluent API ---

class TestFluentAPI:
    def test_full_workflow(self, tmp_db_path):
        tracker.start_run(name="fluent", db_path=tmp_db_path)
        tracker.log_param("lr", 0.01)
        tracker.log_metric("loss", 0.9, step=0)
        tracker.end_run()
        runs = tracker.list_runs(db_path=tmp_db_path)
        assert len(runs) == 1
        assert runs[0]["status"] == "completed"

    def test_log_without_run_raises(self):
        tracker._active_run = None
        with pytest.raises(RuntimeError, match="No active run"):
            tracker.log_param("x", 1)
