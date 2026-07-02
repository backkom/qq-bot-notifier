from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import AppConfig, NotifyRequest


MENTION_RE = re.compile(r"@([A-Za-z0-9_-]+)")


@dataclass
class BuildResult:
    group_id: int
    message: list[dict[str, Any]]
    mentioned_users: list[str] = field(default_factory=list)
    mentioned_qqs: list[str] = field(default_factory=list)
    unknown_mentions: list[str] = field(default_factory=list)


def build_full_text(request: NotifyRequest) -> str:
    chunks: list[str] = []
    if request.title:
        chunks.append(request.title.strip())
    chunks.append(request.text)

    if request.extra:
        extra_lines = []
        for key, value in request.extra.items():
            if value is None or value == "":
                continue
            extra_lines.append(f"{key}: {value}")
        if extra_lines:
            chunks.append("\n".join(extra_lines))

    return "\n".join(chunk for chunk in chunks if chunk)


def build_group_message(config: AppConfig, request: NotifyRequest) -> BuildResult:
    project = config.projects.get(request.project)
    if project is None:
        raise KeyError(f"Unknown project: {request.project}")

    full_text = build_full_text(request)
    message: list[dict[str, Any]] = []
    mentioned_users: list[str] = []
    mentioned_qqs: list[str] = []
    unknown_mentions: list[str] = []
    seen_qqs: set[str] = set()

    last_index = 0
    for match in MENTION_RE.finditer(full_text):
        if match.start() > last_index:
            _append_text(message, full_text[last_index : match.start()])

        mention = match.group(1)
        resolved = _resolve_mention(config, mention)
        if not resolved:
            unknown_mentions.append(mention)
            _append_text(message, match.group(0))
        else:
            for username, qq in resolved:
                if qq in seen_qqs:
                    continue
                seen_qqs.add(qq)
                mentioned_users.append(username)
                mentioned_qqs.append(qq)
                _append_at(message, qq)

        last_index = match.end()

    if last_index < len(full_text):
        _append_text(message, full_text[last_index:])

    if not message:
        _append_text(message, full_text)

    return BuildResult(
        group_id=project.group_id,
        message=message,
        mentioned_users=mentioned_users,
        mentioned_qqs=mentioned_qqs,
        unknown_mentions=unknown_mentions,
    )


def _resolve_mention(config: AppConfig, mention: str) -> list[tuple[str, str]]:
    user = config.users.get(mention)
    if user is not None:
        return [(mention, user.qq)]

    group = config.mention_groups.get(mention)
    if group is None:
        return []

    resolved: list[tuple[str, str]] = []
    for username in group.members:
        member = config.users.get(username)
        if member is not None:
            resolved.append((username, member.qq))
    return resolved


def _append_text(message: list[dict[str, Any]], text: str) -> None:
    if not text:
        return
    if message and message[-1]["type"] == "text":
        message[-1]["data"]["text"] += text
        return
    message.append({"type": "text", "data": {"text": text}})


def _append_at(message: list[dict[str, Any]], qq: str) -> None:
    message.append({"type": "at", "data": {"qq": qq}})
    _append_text(message, " ")

