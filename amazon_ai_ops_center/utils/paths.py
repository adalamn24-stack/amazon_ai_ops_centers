"""Path and lightweight environment helpers for project-local storage."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def load_env_file(env_file: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file without overwriting env vars."""
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / ".env")


def resolve_app_path(value: str | None, default: str) -> Path:
    """Resolve a configured path relative to the application directory."""
    raw_path = Path(value or default).expanduser()
    if raw_path.is_absolute():
        return raw_path
    return BASE_DIR / raw_path


DATA_DIR = resolve_app_path(os.getenv("DATABASE_PATH"), "data/ops_center.sqlite3").parent
DATABASE_PATH = resolve_app_path(os.getenv("DATABASE_PATH"), "data/ops_center.sqlite3")
PROJECTS_DIR = resolve_app_path(os.getenv("PROJECTS_DIR"), "projects")


def ensure_base_directories() -> None:
    """Create the application data directories if they do not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
