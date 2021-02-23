import pytest
from flask.testing import FlaskClient

import bot_prototype


@pytest.fixture
def client() -> FlaskClient:
    """Returns a client which can be used to test the HTTP API."""
    bot_prototype.app.config["TESTING"] = True

    with bot_prototype.app.test_client() as client:
        yield client


def test_send_message(client: FlaskClient):
    response = client.post("/user/test/message", json={"text": "Hello"})

    assert response.status_code == 200
    response_body = response.json

    assert len(response_body) == 2
    assert response_body[0] == "Welcome! Let me tell you a joke."


def test_retrieve_history(client: FlaskClient):
    client.post("/user/test_retrieve/message", json={"text": "Hello"})

    response = client.get("/user/test_retrieve/message")
    assert response.status_code == 200
    history = response.json

    assert len(history) == 3

    assert history[0] == {"message": "Hello", "type": "user"}
    assert history[1] == {"message": "Welcome! Let me tell you a joke.", "type": "bot"}
    assert history[2]["type"] == "bot"
    
    # missing test case to check if no message is passed
    response = client.get("/user/test_unknown/message")
    history = response.json
    assert response.status_code == 404
    assert len(history) == 0
