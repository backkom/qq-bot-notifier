import json

from fastapi.testclient import TestClient

from app import config_store
from app.main import app


def write_config(path) -> None:
    path.write_text(
        json.dumps(
            {
                "qq_bot": {"url": "http://bot/send_group_msg"},
                "users": {
                    "leaf": {"qq": "172310132"},
                    "alice": {"qq": "10001"},
                },
                "mention_groups": {
                    "qa": {"members": ["leaf", "alice"]},
                },
            }
        ),
        encoding="utf-8",
    )


def test_delete_user_removes_user_and_group_membership(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)
    monkeypatch.setattr(config_store, "CONFIG_PATH", config_path)

    config = config_store.delete_user("leaf")

    assert "leaf" not in config.users
    assert config.mention_groups["qa"].members == ["alice"]

    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert "leaf" not in saved["users"]
    assert saved["mention_groups"]["qa"]["members"] == ["alice"]


def test_delete_user_from_web_form_redirects(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)
    monkeypatch.setattr(config_store, "CONFIG_PATH", config_path)

    response = TestClient(app).post("/users/delete", data={"username": "leaf"}, follow_redirects=False)

    assert response.status_code == 303
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert "leaf" not in saved["users"]


def test_add_user_from_web_form_only_saves_username_and_qq(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    write_config(config_path)
    monkeypatch.setattr(config_store, "CONFIG_PATH", config_path)

    response = TestClient(app).post(
        "/users",
        data={"username": "bob", "qq": "10002"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["users"]["bob"] == {"qq": "10002"}
