from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config_store import (
    add_or_update_mention_group,
    add_or_update_project,
    add_or_update_user,
    config_as_public_dict,
    get_config_path,
    load_config,
    validate_config,
)
from .message_parser import build_group_message
from .models import NotifyRequest, NotifyResponse
from .qq_sender import QQBotSendError, send_group_message


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qq-bot-notifier")

app = FastAPI(title="QQ Bot Notifier")
templates = Jinja2Templates(directory="app/templates")


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
    display_name: Annotated[str, Form()] = "",
) -> RedirectResponse:
    add_or_update_user(username.strip(), qq.strip(), display_name.strip())
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

