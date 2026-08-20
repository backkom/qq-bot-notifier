from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config_store import (
    add_or_update_mention_group,
    add_or_update_project,
    add_or_update_user,
    config_as_public_dict,
    delete_user,
    get_config_path,
    load_config,
    validate_config,
)
from .failure_notifier import notify_qq_bot_failure
from .message_parser import build_group_message
from .models import (
    NotifyRequest,
    NotifyResponse,
    CacheMessagesClearResponse,
    CacheMessagesCopyResponse,
    PrivateMessageRequest,
    PrivateMessageResponse,
    ReceivedMessageRequest,
    ReceivedMessageResponse,
)
from .qq_sender import (
    QQBotSendError,
    read_recent_delivery_logs,
    send_group_message,
    send_private_message,
)
from .received_message_store import (
    delete_message,
    delete_messages,
    list_messages_by_project_key,
    receive_message,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qq-bot-notifier")

app = FastAPI(title="QQ Bot Notifier")
templates = Jinja2Templates(directory="app/templates")
_CST = timezone(timedelta(hours=8), name="CST")

def format_cst(value: datetime) -> str:
    return value.astimezone(_CST).strftime("%Y-%m-%d %H:%M:%S CST")


def days_since(value: datetime) -> int:
    """Return the number of complete days elapsed since an aware timestamp."""
    now = datetime.now(timezone.utc)
    return max(0, (now - value.astimezone(timezone.utc)).days)


templates.env.filters["cst_time"] = format_cst
templates.env.filters["days_since"] = days_since


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"ok": "true"}


@app.post("/notify", response_model=NotifyResponse)
async def notify(request: NotifyRequest) -> NotifyResponse:
    config = load_config()
    validation = validate_config(config)
    if not validation.ok:
        raise HTTPException(status_code=500, detail=validation.errors)

    try:
        built = build_group_message(config, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info(
        "notify project=%s group_id=%s mentions=%s unknown=%s",
        request.project,
        built.group_id,
        built.mentioned_users,
        built.unknown_mentions,
    )

    try:
        status = await send_group_message(config.qq_bot, built.group_id, built.message)
    except QQBotSendError as exc:
        notification_content = f"{request.title}\n{request.text}" if request.title else request.text
        await notify_qq_bot_failure(notification_content)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NotifyResponse(
        ok=True,
        project=request.project,
        group_id=built.group_id,
        mentioned_users=built.mentioned_users,
        mentioned_qqs=built.mentioned_qqs,
        unknown_mentions=built.unknown_mentions,
        qq_bot_status=status,
    )


@app.post("/private-message", response_model=PrivateMessageResponse)
async def private_message(request: PrivateMessageRequest) -> PrivateMessageResponse:
    config = load_config()
    logger.info("private_message qq=%s", request.qq)

    try:
        status = await send_private_message(config.qq_bot, request.qq, request.text)
    except QQBotSendError as exc:
        await notify_qq_bot_failure(request.text)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return PrivateMessageResponse(ok=True, qq=request.qq, qq_bot_status=status)


@app.post("/cache-messages", response_model=ReceivedMessageResponse)
def post_received_message(request: ReceivedMessageRequest) -> ReceivedMessageResponse:
    message = receive_message(request.project, request.key, request.message)
    logger.info("received_message project=%s key=%s", request.project, request.key)
    return ReceivedMessageResponse(ok=True, message=message)


@app.get("/cache-messages/copy-all", response_model=CacheMessagesCopyResponse)
def get_cache_messages_copy_all(
    project: Annotated[str, Query(min_length=1)],
    key: Annotated[str, Query(min_length=1)],
) -> CacheMessagesCopyResponse:
    messages = list_messages_by_project_key().get((project, key), [])
    text_messages = [item.message for item in messages]
    return CacheMessagesCopyResponse(
        project=project,
        key=key,
        messages=text_messages,
        content="\n".join(text_messages),
    )


@app.delete("/cache-messages/clear-all", response_model=CacheMessagesClearResponse)
def delete_cache_messages_clear_all(
    project: Annotated[str, Query(min_length=1)],
    key: Annotated[str, Query(min_length=1)],
) -> CacheMessagesClearResponse:
    deleted_count = delete_messages(project, key)
    logger.info("clear_cache_messages project=%s key=%s deleted=%s", project, key, deleted_count)
    return CacheMessagesClearResponse(
        ok=True,
        project=project,
        key=key,
        deleted_count=deleted_count,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    config = load_config()
    validation = validate_config(config)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "config": config,
            "config_path": get_config_path(),
            "delivery_logs": read_recent_delivery_logs(hours=24),
            "received_messages_by_project_key": list_messages_by_project_key(),
            "validation": validation,
        },
    )


@app.get("/config")
def get_config() -> dict:
    return config_as_public_dict(load_config())


@app.get("/config/validate")
def get_config_validation() -> dict:
    return validate_config(load_config()).model_dump(mode="json")


@app.post("/users")
def post_user(
    username: Annotated[str, Form()],
    qq: Annotated[str, Form()],
) -> RedirectResponse:
    add_or_update_user(username.strip(), qq.strip())
    return RedirectResponse("/", status_code=303)


@app.post("/users/delete")
def post_delete_user(username: Annotated[str, Form()]) -> RedirectResponse:
    delete_user(username.strip())
    return RedirectResponse("/", status_code=303)


@app.post("/projects")
def post_project(
    project: Annotated[str, Form()],
    group_id: Annotated[int, Form()],
) -> RedirectResponse:
    add_or_update_project(project.strip(), group_id)
    return RedirectResponse("/", status_code=303)


@app.post("/mention-groups")
def post_mention_group(
    name: Annotated[str, Form()],
    members: Annotated[str, Form()],
) -> RedirectResponse:
    member_names = [member.strip() for member in members.split(",") if member.strip()]
    add_or_update_mention_group(name.strip(), member_names)
    return RedirectResponse("/", status_code=303)


@app.post("/cache-messages/delete")
def post_delete_received_message(message_id: Annotated[str, Form()]) -> RedirectResponse:
    delete_message(message_id)
    return RedirectResponse("/", status_code=303)


@app.post("/cache-messages/delete-group")
def post_delete_received_message_group(
    project: Annotated[str, Form()],
    key: Annotated[str, Form()],
) -> RedirectResponse:
    delete_messages(project, key)
    return RedirectResponse("/", status_code=303)
