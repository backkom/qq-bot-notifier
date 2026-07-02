from app.message_parser import build_group_message
from app.models import AppConfig, NotifyRequest


def make_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "qq_bot": {
                "url": "http://bot/send_group_msg",
                "token": "",
            },
            "projects": {
                "monster": {
                    "group_id": 524653233,
                }
            },
            "users": {
                "leaf": {
                    "qq": "172310132",
                },
                "alice": {
                    "qq": "10001",
                },
                "bob": {
                    "qq": "10002",
                },
            },
            "mention_groups": {
                "monster_tester": {
                    "members": ["alice", "bob"],
                }
            },
        }
    )


def test_user_mention_is_converted_to_at() -> None:
    result = build_group_message(
        make_config(),
        NotifyRequest(project="monster", text="@leaf test msg"),
    )

    assert result.group_id == 524653233
    assert result.mentioned_users == ["leaf"]
    assert result.mentioned_qqs == ["172310132"]
    assert result.message[0] == {"type": "at", "data": {"qq": "172310132"}}


def test_group_mention_is_expanded() -> None:
    result = build_group_message(
        make_config(),
        NotifyRequest(project="monster", text="@monster_tester failed"),
    )

    assert result.mentioned_users == ["alice", "bob"]
    assert result.mentioned_qqs == ["10001", "10002"]


def test_duplicate_qq_is_deduplicated() -> None:
    result = build_group_message(
        make_config(),
        NotifyRequest(project="monster", text="@leaf @leaf @monster_tester"),
    )

    assert result.mentioned_qqs == ["172310132", "10001", "10002"]


def test_unknown_mention_is_kept_as_text() -> None:
    result = build_group_message(
        make_config(),
        NotifyRequest(project="monster", text="@unknown please check"),
    )

    assert result.unknown_mentions == ["unknown"]
    assert result.message[0] == {"type": "text", "data": {"text": "@unknown please check"}}

