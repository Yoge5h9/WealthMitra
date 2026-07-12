"""WS /ws/{space_id}: a chat-triggered rm_lead turn publishes
lead.created to any listener on that space, and events never leak across
spaces.
"""

import json

import pytest
from agent_fakes import FakeGateway, resp
from fastapi.testclient import TestClient

from app.agent import set_orchestrator
from app.agent.orchestrator import Orchestrator
from app.core.spaces import get_space_store
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    yield
    set_orchestrator(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def space_id() -> str:
    return get_space_store().create_space()


def install_fake(script) -> FakeGateway:
    fake = FakeGateway(script)
    set_orchestrator(Orchestrator(fake))
    return fake


def sse_frames(text: str) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in text.splitlines() if line.startswith("data: ")]


def create_session(client, space_id, persona_id="ravi", language=None) -> str:
    body = {"persona_id": persona_id}
    if language:
        body["language"] = language
    response = client.post(f"/api/spaces/{space_id}/sessions", json=body)
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_ws_receives_lead_created_on_chat_triggered_lead(client, space_id):
    install_fake([resp(text="Hello Meera!")])
    sid = create_session(client, space_id, persona_id="meera", language="gu")

    with client.websocket_connect(f"/ws/{space_id}") as ws:
        install_fake([resp(text="A specialist will reach out shortly.")])
        response = client.post("/api/chat", json={"session_id": sid, "message": "I want equity mutual funds"})
        assert response.status_code == 200
        frames = sse_frames(response.text)
        card = next(f["card"] for f in frames if f["type"] == "card")

        event = ws.receive_json()
        assert event["type"] == "lead.created"
        assert event["payload"]["lead_id"] == card["lead_id"]
        assert event["payload"]["family"] == "investment_insurance"


def test_ws_events_are_scoped_to_their_space(client, space_id):
    other_space = get_space_store().create_space()
    with client.websocket_connect(f"/ws/{other_space}") as ws:
        assert client.post(f"/api/spaces/{space_id}/reset").status_code == 200
        assert client.post(f"/api/spaces/{other_space}/reset").status_code == 200

        event = ws.receive_json()
        assert event["type"] == "space.reset"
        assert event["payload"]["space_id"] == other_space


def test_ws_disconnect_cleans_up_subscriber(client, space_id):
    from app.core import events

    with client.websocket_connect(f"/ws/{space_id}"):
        assert space_id in events._subscribers

    assert space_id not in events._subscribers
