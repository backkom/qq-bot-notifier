import json
from datetime import datetime, timedelta, timezone

from app import qq_sender


def write_log(path, entries) -> None:
    path.write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n",
        encoding="utf-8",
    )


def test_read_recent_delivery_logs_returns_last_24_hours(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "qqbot-payloads.jsonl"
    now = datetime.now(timezone.utc)
    write_log(
        log_path,
        [
            {
                "timestamp": (now - timedelta(hours=25)).isoformat(),
                "url": "http://bot/send_group_msg",
                "payload": {"group_id": 1, "message": [{"type": "text", "data": {"text": "old"}}]},
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "url": "http://bot/send_group_msg",
                "payload": {
                    "group_id": 2,
                    "message": [
                        {"type": "at", "data": {"qq": "172310132"}},
                        {"type": "text", "data": {"text": " hello"}},
                    ],
                },
            },
        ],
    )
    monkeypatch.setattr(qq_sender, "DELIVERY_LOG_PATH", log_path)

    records = qq_sender.read_recent_delivery_logs(hours=24)

    assert len(records) == 1
    assert records[0]["group_id"] == 2
    assert records[0]["message_preview"] == "@172310132  hello"


def test_read_recent_delivery_logs_skips_invalid_lines(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "qqbot-payloads.jsonl"
    now = datetime.now(timezone.utc)
    log_path.write_text(
        "not json\n"
        + json.dumps(
            {
                "timestamp": now.isoformat(),
                "url": "http://bot/send_group_msg",
                "payload": {"group_id": 3, "message": [{"type": "text", "data": {"text": "ok"}}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(qq_sender, "DELIVERY_LOG_PATH", log_path)

    records = qq_sender.read_recent_delivery_logs(hours=24)

    assert len(records) == 1
    assert records[0]["message_preview"] == "ok"
