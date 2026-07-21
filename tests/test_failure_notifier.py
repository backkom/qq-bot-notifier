import base64
from unittest.mock import AsyncMock

import pytest
import respx
from fastapi import HTTPException
from httpx import Response

from app import failure_notifier, main
from app.failure_notifier import notify_qq_bot_failure
from app.models import AppConfig, NotifyRequest
from app.qq_sender import QQBotSendError


@pytest.mark.anyio
@respx.mock
async def test_notify_qq_bot_failure_posts_jenkins_form(monkeypatch) -> None:
    url = "http://jenkins/job/notify/buildWithParameters"
    route = respx.post(url).mock(return_value=Response(201))
    monkeypatch.setattr(failure_notifier, "NOTIFY_URL", url)
    monkeypatch.setattr(failure_notifier, "NOTIFY_USERNAME", "user")
    monkeypatch.setattr(failure_notifier, "NOTIFY_PASSWORD", "token")

    await notify_qq_bot_failure("monster 构建失败")

    request = route.calls.last.request
    expected_auth = base64.b64encode(b"user:token").decode("ascii")
    assert request.headers["Authorization"] == f"Basic {expected_auth}"
    assert request.headers["Content-Type"].startswith("application/x-www-form-urlencoded")
    assert request.content.decode("ascii") == (
        "target=192.168.0.194%3B&text=%E7%BB%99QQBot%E5%8F%91%E9%80%81%E6%B6%88%E6%81%AF%E5%A4%B1%E8%B4%A5"
        "%0A%E9%80%9A%E7%9F%A5%E5%86%85%E5%AE%B9%EF%BC%9Amonster+%E6%9E%84%E5%BB%BA%E5%A4%B1%E8%B4%A5"
    )


@pytest.mark.anyio
async def test_notify_reports_qq_bot_failure_and_returns_502(monkeypatch) -> None:
    config = AppConfig.model_validate(
        {
            "qq_bot": {"url": "http://bot/send_group_msg"},
            "projects": {"monster": {"group_id": 524653233}},
        }
    )
    send = AsyncMock(side_effect=QQBotSendError("QQ bot unavailable"))
    report_failure = AsyncMock()
    monkeypatch.setattr(main, "load_config", lambda: config)
    monkeypatch.setattr(main, "send_group_message", send)
    monkeypatch.setattr(main, "notify_qq_bot_failure", report_failure)

    with pytest.raises(HTTPException) as exc_info:
        await main.notify(NotifyRequest(project="monster", title="构建失败", text="build failed"))

    assert exc_info.value.status_code == 502
    report_failure.assert_awaited_once_with("构建失败\nbuild failed")
