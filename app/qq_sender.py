from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import httpx

from .models import QQBotConfig


class QQBotSendError(RuntimeError):
    pass


DELIVERY_LOG_PATH = Path(os.getenv("QQ_DELIVERY_LOG", "logs/qqbot-payloads.jsonl"))
_DELIVERY_LOG_LOCK = RLock()


async def send_group_message(
    qq_bot: QQBotConfig,
    group_id: int,
    message: list[dict[str, Any]],
) -> int:
    headers = {"Content-Type": "application/json"}
    if qq_bot.token:
        headers["Authorization"] = f"Bearer {qq_bot.token}"

    payload = {
        "group_id": group_id,
        "message": message,
    }

    write_delivery_log(qq_bot.url, payload)

    async with httpx.AsyncClient(timeout=qq_bot.timeout_seconds) as client:
        response = await client.post(qq_bot.url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise QQBotSendError(f"QQ bot returned {response.status_code}: {response.text[:500]}")

    return response.status_code


def write_delivery_log(url: str, payload: dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "payload": payload,
    }
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))

    with _DELIVERY_LOG_LOCK:
        DELIVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DELIVERY_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
