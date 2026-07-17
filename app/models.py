from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 7848


class QQBotConfig(BaseModel):
    url: str
    token: str = ""
    timeout_seconds: float = 10


class ProjectConfig(BaseModel):
    group_id: int


class UserConfig(BaseModel):
    qq: str


class MentionGroupConfig(BaseModel):
    members: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: ServerConfig = Field(default_factory=ServerConfig)
    qq_bot: QQBotConfig
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)
    users: dict[str, UserConfig] = Field(default_factory=dict)
    mention_groups: dict[str, MentionGroupConfig] = Field(default_factory=dict)


class NotifyRequest(BaseModel):
    project: str
    text: str
    title: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NotifyResponse(BaseModel):
    ok: bool
    project: str
    group_id: int
    mentioned_users: list[str]
    mentioned_qqs: list[str]
    unknown_mentions: list[str]
    qq_bot_status: int | None = None


class ConfigValidationResult(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
