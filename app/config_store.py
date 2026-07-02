from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from .env_loader import load_project_env
from .models import AppConfig, ConfigValidationResult, MentionGroupConfig, ProjectConfig, UserConfig


load_project_env()

CONFIG_PATH = Path(os.getenv("QQ_NOTIFIER_CONFIG", "config/config.json"))
_LOCK = RLock()


def get_config_path() -> Path:
    return CONFIG_PATH


def load_config() -> AppConfig:
    with _LOCK:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        token = os.getenv("QQ_BOT_TOKEN")
        if token:
            raw.setdefault("qq_bot", {})["token"] = token
        return AppConfig.model_validate(raw)


def save_config(config: AppConfig) -> None:
    with _LOCK:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
        data = config.model_dump(mode="json")
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(CONFIG_PATH)


def validate_config(config: AppConfig) -> ConfigValidationResult:
    errors: list[str] = []

    if not config.qq_bot.url:
        errors.append("qq_bot.url is required")

    for project, project_config in config.projects.items():
        if project_config.group_id <= 0:
            errors.append(f"projects.{project}.group_id must be positive")

    for username, user in config.users.items():
        if not user.qq.strip():
            errors.append(f"users.{username}.qq is required")
        if not user.qq.isdigit():
            errors.append(f"users.{username}.qq must contain digits only")

    for group_name, group in config.mention_groups.items():
        for member in group.members:
            if member not in config.users:
                errors.append(f"mention_groups.{group_name} references unknown user: {member}")

    return ConfigValidationResult(ok=not errors, errors=errors)


def add_or_update_user(username: str, qq: str, display_name: str = "") -> AppConfig:
    config = load_config()
    config.users[username] = UserConfig(qq=qq, display_name=display_name)
    save_config(config)
    return config


def delete_user(username: str) -> AppConfig:
    config = load_config()
    config.users.pop(username, None)
    for group in config.mention_groups.values():
        group.members = [member for member in group.members if member != username]
    save_config(config)
    return config


def add_or_update_project(project: str, group_id: int) -> AppConfig:
    config = load_config()
    config.projects[project] = ProjectConfig(group_id=group_id)
    save_config(config)
    return config


def add_or_update_mention_group(name: str, members: list[str]) -> AppConfig:
    config = load_config()
    config.mention_groups[name] = MentionGroupConfig(members=members)
    save_config(config)
    return config


def config_as_public_dict(config: AppConfig) -> dict[str, Any]:
    data = config.model_dump(mode="json")
    if data.get("qq_bot", {}).get("token"):
        data["qq_bot"]["token"] = "***"
    return data
