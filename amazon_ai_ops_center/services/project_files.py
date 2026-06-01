"""Filesystem helpers for per-project folders."""

from __future__ import annotations

from pathlib import Path

from utils.paths import PROJECTS_DIR


def project_root(project_id: str) -> Path:
    """Return the root folder for a project."""
    return PROJECTS_DIR / project_id


def create_project_folders(project_id: str) -> None:
    """Create the required folder tree for a project."""
    root = project_root(project_id)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    (root / "outputs").mkdir(parents=True, exist_ok=True)


def delete_project_folders(project_id: str) -> None:
    """Delete a project's local folder tree if it is safe to do so."""
    root = project_root(project_id).resolve()
    projects_root = PROJECTS_DIR.resolve()
    if not root.exists():
        return
    if projects_root not in root.parents:
        raise ValueError(f"Refusing to delete path outside projects directory: {root}")

    for child in sorted(root.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    root.rmdir()
