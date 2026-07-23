from fastapi.testclient import TestClient

from app import received_message_store
from app.main import app


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
