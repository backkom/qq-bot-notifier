from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .env_loader import load_project_env
from .models import ReceivedMessage


load_project_env()

RECEIVED_MESSAGES_PATH = Path(os.getenv("QQ_RECEIVED_MESSAGES", "logs/received-messages.json"))
_LOCK = RLock()


def receive_message(
    project: str,
    key: str,
    message: str,
    payload: Any = None,
) -> ReceivedMessage:
    """Insert a message or refresh an identical message with its latest payload."""
    now = datetime.now(UTC)
    with _LOCK:
        messages = _load_messages()
        for item in messages:
            if item.project == project and item.key == key and item.message == message:
                item.received_at = now
                item.payload = payload
                _save_messages(messages)
                return item

        item = ReceivedMessage(
            id=str(uuid4()),
            project=project,
            key=key,
            message=message,
            payload=payload,
            first_received_at=now,
            received_at=now,
        )
        messages.append(item)
        _save_messages(messages)
        return item


def list_messages_by_project_key() -> dict[tuple[str, str], list[ReceivedMessage]]:
    with _LOCK:
        grouped: dict[tuple[str, str], list[ReceivedMessage]] = {}
        for item in _load_messages():
            grouped.setdefault((item.project, item.key), []).append(item)

        for messages in grouped.values():
            messages.sort(key=lambda item: item.received_at, reverse=True)

        return dict(
            sorted(
                grouped.items(),
                key=lambda group: group[1][0].received_at,
                reverse=True,
            )
        )


def delete_message(message_id: str) -> bool:
    with _LOCK:
        messages = _load_messages()
        remaining = [item for item in messages if item.id != message_id]
        if len(remaining) == len(messages):
            return False
        _save_messages(remaining)
        return True


def delete_messages(project: str, key: str) -> int:
    """Delete every message belonging to a project and key pair."""
    with _LOCK:
        messages = _load_messages()
        remaining = [
            item for item in messages if item.project != project or item.key != key
        ]
        deleted_count = len(messages) - len(remaining)
        if deleted_count:
            _save_messages(remaining)
        return deleted_count


def _load_messages() -> list[ReceivedMessage]:
    if not RECEIVED_MESSAGES_PATH.exists():
        return []
    raw = json.loads(RECEIVED_MESSAGES_PATH.read_text(encoding="utf-8"))
    messages = []
    for item in raw:
        if not item.get("first_received_at"):
            item = {**item, "first_received_at": item["received_at"]}
        messages.append(ReceivedMessage.model_validate(item))
    return messages


def _save_messages(messages: list[ReceivedMessage]) -> None:
    RECEIVED_MESSAGES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = RECEIVED_MESSAGES_PATH.with_suffix(RECEIVED_MESSAGES_PATH.suffix + ".tmp")
    data = [item.model_dump(mode="json") for item in messages]
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(RECEIVED_MESSAGES_PATH)
