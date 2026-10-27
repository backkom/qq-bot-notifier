from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app import main
from app.models import AppConfig, NotifyRequest, PrivateMessageRequest
from app.qq_sender import QQBotSendError


@pytest.mark.anyio
async def test_notify_returns_502_when_qq_bot_fails(monkeypatch) -> None:
    config = AppConfig.model_validate(
        {
            "qq_bot": {"url": "http://bot/send_group_msg"},
            "projects": {"monster": {"group_id": 524653233}},
        }
    )
    send = AsyncMock(side_effect=QQBotSendError("QQ bot unavailable"))
    monkeypatch.setattr(main, "load_config", lambda: config)
    monkeypatch.setattr(main, "send_group_message", send)

    with pytest.raises(HTTPException) as exc_info:
        await main.notify(NotifyRequest(project="monster", title="构建失败", text="build failed"))

    assert exc_info.value.status_code == 502
    send.assert_awaited_once()


@pytest.mark.anyio
async def test_private_message_returns_502_when_qq_bot_fails(monkeypatch) -> None:
    config = AppConfig.model_validate({"qq_bot": {"url": "http://bot/send_group_msg"}})
    send = AsyncMock(side_effect=QQBotSendError("QQ bot unavailable"))
    monkeypatch.setattr(main, "load_config", lambda: config)
    monkeypatch.setattr(main, "send_private_message", send)

    with pytest.raises(HTTPException) as exc_info:
        await main.private_message(PrivateMessageRequest(qq="172310132", text="hello"))

    assert exc_info.value.status_code == 502
    send.assert_awaited_once()
