from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    root = project_root()
    path = Path(config_path) if config_path else root / "configs" / "project.toml"
    if not path.is_absolute():
        path = root / path
    with path.open("rb") as fh:
        cfg = tomllib.load(fh)
    cfg["_project_root"] = str(root)
    cfg["_config_path"] = str(path)
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    root = Path(cfg["_project_root"])
    value = cfg["paths"][key]
    path = Path(value)
    return path if path.is_absolute() else root / path


def ensure_directories(cfg: dict[str, Any]) -> None:
    for key in ("data_dir", "raw_dir", "processed_dir", "reports_dir", "logs_dir"):
        resolve_path(cfg, key).mkdir(parents=True, exist_ok=True)
