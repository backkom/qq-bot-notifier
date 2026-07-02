from app.config_store import validate_config
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

