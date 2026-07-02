from __future__ import annotations

from typing import Any

import httpx

from .models import QQBotConfig


class QQBotSendError(RuntimeError):
    pass


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

    async with httpx.AsyncClient(timeout=qq_bot.timeout_seconds) as client:
        response = await client.post(qq_bot.url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise QQBotSendError(f"QQ bot returned {response.status_code}: {response.text[:500]}")

    return response.status_code

