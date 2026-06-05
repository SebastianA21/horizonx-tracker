import uuid
import datetime
import pathlib
import shutil


def generate_run_id() -> str:
    return uuid.uuid4().hex  # 32-char hex, no hyphens


def now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_artifact_dir(base_dir: str, run_id: str) -> pathlib.Path:
    p = pathlib.Path(base_dir) / "artifacts" / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def copy_artifact(src: str, dest_dir: pathlib.Path, name: str = None) -> tuple[str, int]:
    src_path = pathlib.Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Artifact source not found: {src}")
    dest_name = name or src_path.name
    dest = dest_dir / dest_name
    shutil.copy2(str(src_path), str(dest))
    return str(dest), dest.stat().st_size
