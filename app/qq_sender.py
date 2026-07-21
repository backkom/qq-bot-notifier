from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from .env_loader import load_project_env
from .models import QQBotConfig


class QQBotSendError(RuntimeError):
    pass


load_project_env()

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

    try:
        async with httpx.AsyncClient(timeout=qq_bot.timeout_seconds) as client:
            response = await client.post(qq_bot.url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        write_delivery_log(
            qq_bot.url,
            payload,
            success=False,
            status_code=None,
            result_text=str(exc),
        )
        raise QQBotSendError(f"Failed to call QQ bot: {exc}") from exc

    success = response.status_code < 400
    write_delivery_log(
        qq_bot.url,
        payload,
        success=success,
        status_code=response.status_code,
        result_text=response.text[:500],
    )

    if not success:
        raise QQBotSendError(f"QQ bot returned {response.status_code}: {response.text[:500]}")

    return response.status_code


async def send_private_message(qq_bot: QQBotConfig, qq: str, text: str) -> int:
    url = _private_message_url(qq_bot.url)
    headers = {"Content-Type": "application/json"}
    if qq_bot.token:
        headers["Authorization"] = f"Bearer {qq_bot.token}"

    # NapCat's send_private_msg schema accepts user_id and message as strings.
    payload = {"user_id": qq, "message": text}

    try:
        async with httpx.AsyncClient(timeout=qq_bot.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        write_delivery_log(url, payload, success=False, status_code=None, result_text=str(exc))
        raise QQBotSendError(f"Failed to call QQ bot: {exc}") from exc

    result_text = response.text[:500]
    success = response.status_code < 400 and _napcat_response_succeeded(response)
    write_delivery_log(
        url,
        payload,
        success=success,
        status_code=response.status_code,
        result_text=result_text,
    )

    if not success:
        raise QQBotSendError(f"QQ bot returned {response.status_code}: {result_text}")

    return response.status_code


def _private_message_url(group_message_url: str) -> str:
    parsed = urlsplit(group_message_url)
    return urlunsplit(parsed._replace(path="/send_private_msg", query="", fragment=""))


def _napcat_response_succeeded(response: httpx.Response) -> bool:
    try:
        body = response.json()
    except ValueError:
        return True

    if not isinstance(body, dict) or "status" not in body:
        return True
    return body.get("status") == "ok" and body.get("retcode", 0) == 0


def write_delivery_log(
    url: str,
    payload: dict[str, Any],
    *,
    success: bool | None = None,
    status_code: int | None = None,
    result_text: str = "",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "payload": payload,
        "success": success,
        "status_code": status_code,
        "result_text": result_text,
    }
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))

    with _DELIVERY_LOG_LOCK:
        DELIVERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DELIVERY_LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def read_recent_delivery_logs(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    if not DELIVERY_LOG_PATH.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records: list[dict[str, Any]] = []

    with _DELIVERY_LOG_LOCK:
        lines = DELIVERY_LOG_PATH.read_text(encoding="utf-8").splitlines()

    for line in reversed(lines):
        try:
            entry = json.loads(line)
            timestamp = _parse_log_timestamp(entry.get("timestamp", ""))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

        if timestamp < cutoff:
            continue

        payload = entry.get("payload", {})
        records.append(
            {
                "timestamp": timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
                "url": entry.get("url", ""),
                "group_id": payload.get("group_id", ""),
                "message_preview": _message_preview(payload.get("message", [])),
                "message_full": _message_full(payload.get("message", [])),
                "success": entry.get("success"),
                "status_code": entry.get("status_code"),
                "result_text": _truncate_text(str(entry.get("result_text", "")), limit=180),
            }
        )
        if len(records) >= limit:
            break

    return records


def _parse_log_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _message_preview(message: Any) -> str:
    preview = _message_full(message)
    return _truncate_text(preview, limit=180)


def _message_full(message: Any) -> str:
    if isinstance(message, str):
        return message
    if not isinstance(message, list):
        return str(message)

    parts: list[str] = []
    for segment in message:
        if not isinstance(segment, dict):
            parts.append(str(segment))
            continue
        data = segment.get("data", {})
        if segment.get("type") == "at":
            parts.append(f"@{data.get('qq', '')}")
        elif segment.get("type") == "text":
            parts.append(str(data.get("text", "")))
        else:
            parts.append(f"[{segment.get('type', 'unknown')}]")

    return " ".join(part for part in parts if part).strip()


def _truncate_text(value: str, limit: int) -> str:
    if len(value) > limit:
        return value[: limit - 3] + "..."
    return value
