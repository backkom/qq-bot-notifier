from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app import received_message_store
from app.main import app, format_cst


def test_format_cst_converts_utc_to_china_standard_time() -> None:
    timestamp = datetime(2026, 7, 23, 4, 5, 6, tzinfo=UTC)

    assert format_cst(timestamp) == "2026-07-23 12:05:06 CST"


def test_receive_message_deduplicates_and_refreshes_time(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)

    first = received_message_store.receive_message("api", "build-42", "failed")
    second = received_message_store.receive_message("api", "build-42", "failed")

    assert first.id == second.id
    assert second.received_at >= first.received_at
    grouped = received_message_store.list_messages_by_project_key()
    assert [item.message for item in grouped[("api", "build-42")]] == ["failed"]


def test_delete_allows_the_message_to_be_received_again(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)

    first = received_message_store.receive_message("api", "build-42", "failed")
    assert received_message_store.delete_message(first.id) is True
    second = received_message_store.receive_message("api", "build-42", "failed")

    assert second.id != first.id


def test_delete_messages_removes_only_the_selected_project_key(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)
    received_message_store.receive_message("api", "build-42", "failed")
    received_message_store.receive_message("api", "build-42", "restarted")
    received_message_store.receive_message("api", "build-43", "succeeded")

    assert received_message_store.delete_messages("api", "build-42") == 2
    grouped = received_message_store.list_messages_by_project_key()
    assert list(grouped) == [("api", "build-43")]


def test_received_message_api_and_delete_form(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)
    client = TestClient(app)

    response = client.post(
        "/cache-messages",
        json={"project": "api", "key": "build-42", "message": "failed"},
    )

    assert response.status_code == 200
    message_id = response.json()["message"]["id"]
    delete_response = client.post(
        "/cache-messages/delete",
        data={"message_id": message_id},
        follow_redirects=False,
    )
    assert delete_response.status_code == 303
    assert received_message_store.list_messages_by_project_key() == {}


def test_delete_message_group_form(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)
    client = TestClient(app)
    client.post(
        "/cache-messages",
        json={"project": "api", "key": "build-42", "message": "failed"},
    )

    response = client.post(
        "/cache-messages/delete-group",
        data={"project": "api", "key": "build-42"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert received_message_store.list_messages_by_project_key() == {}


def test_external_copy_all_and_clear_all_apis(tmp_path, monkeypatch) -> None:
    message_path = tmp_path / "received-messages.json"
    monkeypatch.setattr(received_message_store, "RECEIVED_MESSAGES_PATH", message_path)
    client = TestClient(app)
    payload = {"project": "api", "key": "build-42"}
    client.post("/cache-messages", json={**payload, "message": "first"})
    client.post("/cache-messages", json={**payload, "message": "second"})

    copy_response = client.get("/cache-messages/copy-all", params=payload)

    assert copy_response.status_code == 200
    assert copy_response.json()["content"] == "second\nfirst"
    clear_response = client.delete("/cache-messages/clear-all", params=payload)
    assert clear_response.status_code == 200
    assert clear_response.json()["deleted_count"] == 2
    assert received_message_store.list_messages_by_project_key() == {}
