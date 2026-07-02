import os

from app.env_loader import load_env_file


def test_load_env_file_sets_missing_values(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        """
QQ_BOT_TOKEN="from-file"
export QQ_DELIVERY_LOG=logs/custom.jsonl
IGNORED_LINE
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("QQ_BOT_TOKEN", raising=False)
    monkeypatch.delenv("QQ_DELIVERY_LOG", raising=False)

    load_env_file(env_path)

    assert os.environ["QQ_BOT_TOKEN"] == "from-file"
    assert os.environ["QQ_DELIVERY_LOG"] == "logs/custom.jsonl"


def test_load_env_file_does_not_override_existing_values(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("QQ_BOT_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setenv("QQ_BOT_TOKEN", "from-process")

    load_env_file(env_path)

    assert os.environ["QQ_BOT_TOKEN"] == "from-process"
