import json

from app import config_store
from app.config_store import save_config, validate_config
from app.models import AppConfig


def test_validate_config_reports_unknown_group_member() -> None:
    config = AppConfig.model_validate(
        {
            "qq_bot": {"url": "http://bot/send_group_msg"},
            "mention_groups": {
                "qa": {
                    "members": ["missing"],
                }
            },
        }
    )

    result = validate_config(config)

    assert not result.ok
    assert "mention_groups.qa references unknown user: missing" in result.errors


def _sample_config(token: str) -> AppConfig:
    return AppConfig.model_validate(
        {
            "qq_bot": {"url": "http://bot/send_group_msg", "token": token},
            "projects": {"monster": {"group_id": 524653233}},
        }
    )


def test_save_config_strips_token_when_env_provided(tmp_path, monkeypatch) -> None:
    target = tmp_path / "config.json"
    monkeypatch.setattr(config_store, "CONFIG_PATH", target)
    monkeypatch.setenv("QQ_BOT_TOKEN", "env-token")

    save_config(_sample_config("env-token"))

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["qq_bot"]["token"] == ""


def test_save_config_keeps_file_token_when_no_env(tmp_path, monkeypatch) -> None:
    target = tmp_path / "config.json"
    monkeypatch.setattr(config_store, "CONFIG_PATH", target)
    monkeypatch.delenv("QQ_BOT_TOKEN", raising=False)

    save_config(_sample_config("file-token"))

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["qq_bot"]["token"] == "file-token"

