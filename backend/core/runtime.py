"""Runtime paths and deployment policy for the local H3 appliance."""

from __future__ import annotations

import os
import re
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _path_from_env(name: str, fallback: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser().resolve() if value else fallback.resolve()


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATA_ROOT = _path_from_env("AIALRA_DATA_ROOT", BACKEND_DIR / "assets")
VAULT_DIR = DATA_ROOT
JOB_DB = _path_from_env("AIALRA_JOB_DB", DATA_ROOT / "jobs.sqlite3")
LOCAL_ONLY = env_flag("AIALRA_LOCAL_ONLY", default=True)
LOCKED_MODE = env_flag("AIALRA_LOCKED_MODE", default=False)
H3_APPLIANCE = env_flag("AIALRA_H3_APPLIANCE", default=False)


def cors_origins() -> list[str]:
    configured = os.getenv("AIALRA_CORS_ORIGINS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    return [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


for directory in (DATA_ROOT, JOB_DB.parent):
    directory.mkdir(parents=True, exist_ok=True)


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def safe_identifier(value: str, label: str = "identifier") -> str:
    if not _SAFE_ID.fullmatch(value or "") or value in {".", ".."}:
        raise ValueError(f"Invalid {label}")
    return value


def path_within(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    candidate.relative_to(root.resolve())
    return candidate


def project_dir(project_id: str, create: bool = True) -> Path:
    directory = path_within(VAULT_DIR, safe_identifier(project_id, "project_id"))
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_asset_url(asset_url: str) -> Path:
    prefix = "/assets/"
    if not asset_url.startswith(prefix):
        raise ValueError("Expected a local /assets/ URL")
    relative = asset_url[len(prefix):].replace("\\", "/")
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise ValueError("Invalid asset URL")
    return path_within(VAULT_DIR, *relative.split("/"))
