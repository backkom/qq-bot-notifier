from __future__ import annotations

import os
from pathlib import Path


def load_project_env() -> None:
    explicit_path = os.getenv("QQ_ENV_FILE")
    paths = [Path(explicit_path)] if explicit_path else [_project_root() / ".env", Path.cwd() / ".env"]

    for path in paths:
        if path.exists():
            load_env_file(path)


def load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = _clean_env_value(value.strip())


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent
