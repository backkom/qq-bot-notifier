from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("qq-bot-notifier")

NOTIFY_URL = "http://192.168.0.195:8080/job/Others/job/Message%20Notify/buildWithParameters"
NOTIFY_USERNAME = "bigkraken"
NOTIFY_PASSWORD = "11e04fc49296fdac39836d5f4cae91cbcd"
NOTIFY_TARGET = "192.168.0.194;"
NOTIFY_MESSAGE_PREFIX = "给QQBot发送消息失败\n通知内容："
NOTIFY_TIMEOUT_SECONDS = 10.0


async def notify_qq_bot_failure(content: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=NOTIFY_TIMEOUT_SECONDS) as client:
            response = await client.post(
                NOTIFY_URL,
                auth=(NOTIFY_USERNAME, NOTIFY_PASSWORD),
                data={"target": NOTIFY_TARGET, "text": f"{NOTIFY_MESSAGE_PREFIX}{content}"},
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to send QQ bot failure notification: %s", exc)
