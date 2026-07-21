import json

import pytest
import respx
from httpx import Response

from app.models import QQBotConfig
from app import qq_sender
from app.qq_sender import send_group_message, send_private_message


@pytest.mark.anyio
@respx.mock
async def test_send_group_message_posts_expected_payload() -> None:
    route = respx.post("http://bot/send_group_msg").mock(return_value=Response(200, json={"ok": True}))

    status = await send_group_message(
        QQBotConfig(url="http://bot/send_group_msg", token="secret"),
        524653233,
        [{"type": "at", "data": {"qq": "172310132"}}],
    )

    assert status == 200
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.headers["Content-Type"] == "application/json"
    assert request.content == (
        b'{"group_id":524653233,'
        b'"message":[{"type":"at","data":{"qq":"172310132"}}]}'
    )


@pytest.mark.anyio
@respx.mock
async def test_send_group_message_writes_payload_log(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "qqbot-payloads.jsonl"
    monkeypatch.setattr(qq_sender, "DELIVERY_LOG_PATH", log_path)
    respx.post("http://bot/send_group_msg").mock(return_value=Response(200, json={"ok": True}))

    await send_group_message(
        QQBotConfig(url="http://bot/send_group_msg", token="secret"),
        524653233,
        [{"type": "text", "data": {"text": "hello"}}],
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["url"] == "http://bot/send_group_msg"
    assert entry["payload"] == {
        "group_id": 524653233,
        "message": [{"type": "text", "data": {"text": "hello"}}],
    }
    assert entry["success"] is True
    assert entry["status_code"] == 200
    assert entry["result_text"] == '{"ok":true}'
    assert "secret" not in lines[0]


@pytest.mark.anyio
@respx.mock
async def test_send_private_message_posts_napcat_payload() -> None:
    route = respx.post("http://bot/send_private_msg").mock(
        return_value=Response(200, json={"status": "ok", "retcode": 0})
    )

    status = await send_private_message(
        QQBotConfig(url="http://bot/send_group_msg", token="secret"),
        "172310132",
        "hello",
    )

    assert status == 200
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.content == b'{"user_id":"172310132","message":"hello"}'


@pytest.mark.anyio
@respx.mock
async def test_send_private_message_rejects_napcat_failed_response() -> None:
    respx.post("http://bot/send_private_msg").mock(
        return_value=Response(
            200,
            json={"status": "failed", "retcode": 1200, "message": "send failed"},
        )
    )

    with pytest.raises(qq_sender.QQBotSendError, match="send failed"):
        await send_private_message(
            QQBotConfig(url="http://bot/send_group_msg"),
            "172310132",
            "hello",
        )
