"""SQLite persistence for projects and project profile data."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from services.project_files import create_project_folders, delete_project_folders
from utils.paths import DATABASE_PATH, ensure_base_directories


@dataclass(slots=True)
class Project:
    """A product project tracked by the command center."""

    id: str
    name: str
    site: str
    brand: str
    category: str
    core_parameters: str
    target_audience: str
    use_scenarios: str
    compliance_sensitive_words: str
    created_at: str
    updated_at: str


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with row access enabled."""
    ensure_base_directories()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    """Create database tables required by the first-phase application."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                site TEXT DEFAULT '',
                brand TEXT DEFAULT '',
                category TEXT DEFAULT '',
                core_parameters TEXT DEFAULT '',
                target_audience TEXT DEFAULT '',
                use_scenarios TEXT DEFAULT '',
                compliance_sensitive_words TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        site=row["site"],
        brand=row["brand"],
        category=row["category"],
        core_parameters=row["core_parameters"],
        target_audience=row["target_audience"],
        use_scenarios=row["use_scenarios"],
        compliance_sensitive_words=row["compliance_sensitive_words"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_projects() -> list[Project]:
    """Return all projects ordered by update time."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    return [_row_to_project(row) for row in rows]


def get_project(project_id: str | None) -> Project | None:
    """Load a project by ID."""
    if not project_id:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None


def create_project(name: str, site: str = "") -> Project:
    """Create a new project and its independent uploads/outputs folders."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    project_id = uuid.uuid4().hex
    project_name = name.strip() or "未命名产品项目"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id, name, site, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, project_name, site.strip(), now, now),
        )
    create_project_folders(project_id)
    return get_project(project_id)  # type: ignore[return-value]


def update_project(project_id: str, values: dict[str, str]) -> None:
    """Update editable project profile fields."""
    allowed_fields = {
        "name",
        "site",
        "brand",
        "category",
        "core_parameters",
        "target_audience",
        "use_scenarios",
        "compliance_sensitive_words",
    }
    clean_values = {key: value.strip() for key, value in values.items() if key in allowed_fields}
    if not clean_values:
        return

    clean_values["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    assignments = ", ".join(f"{field} = ?" for field in clean_values)
    params = [*clean_values.values(), project_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE projects SET {assignments} WHERE id = ?", params)


def delete_project(project_id: str) -> None:
    """Delete a project record and its local folder tree."""
    with get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    delete_project_folders(project_id)
