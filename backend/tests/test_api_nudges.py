"""GET /api/customer/{session_id}/nudges (Task 13): generates a persona-scoped
feed, caches it per (space, persona) for the day, and publishes `nudge.created`
only for ids the space hasn't already recorded — a same-day refresh never
re-publishes.
"""

import pytest
from agent_fakes import FakeGateway, resp
from fastapi.testclient import TestClient

import app.api.nudges as nudges_module
from app.agent import set_orchestrator
from app.agent.orchestrator import Orchestrator
from app.core.spaces import get_space_store
from app.main import create_app
from app.nudges import set_gateway as set_nudge_gateway


@pytest.fixture(autouse=True)
def _fake_llm_seams():
    # The endpoint phrases copy via the engine's default gateway; inject a
    # fake so no test ever reaches a live provider. FakeGateway's fallback
    # text carries no TITLE:/BODY: markers, so copy deterministically falls
    # back to the i18n templates — stable assertions, zero LLM calls.
    set_nudge_gateway(FakeGateway([]))
    yield
    set_nudge_gateway(None)
    set_orchestrator(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def space_id() -> str:
    return get_space_store().create_space()


def install_fake(script=None) -> FakeGateway:
    fake = FakeGateway(script or [resp(text="Hello!")])
    set_orchestrator(Orchestrator(fake))
    return fake


def create_session(client, space_id, persona_id) -> str:
    response = client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": persona_id})
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_get_nudges_returns_persona_scoped_feed(client, space_id):
    install_fake()
    sid = create_session(client, space_id, "ravi")

    response = client.get(f"/api/customer/{sid}/nudges")
    assert response.status_code == 200
    nudges = response.json()
    assert nudges
    for n in nudges:
        assert n["persona_id"] == "ravi"
        assert n["title"] and n["body"]
        assert n["kind"] in ("functional", "relational")


def test_get_nudges_unknown_session_404(client):
    assert client.get("/api/customer/sess_ghost/nudges").status_code == 404


def test_repeat_get_same_day_is_cached_and_does_not_republish(client, space_id, monkeypatch):
    install_fake()
    sid = create_session(client, space_id, "ravi")

    published: list[dict] = []
    monkeypatch.setattr(nudges_module.events, "publish", lambda space_id, event: published.append(event))

    first = client.get(f"/api/customer/{sid}/nudges").json()
    assert first
    assert len(published) == len(first)
    assert all(e["type"] == "nudge.created" for e in published)
    assert {e["payload"]["id"] for e in published} == {n["id"] for n in first}

    published.clear()
    second = client.get(f"/api/customer/{sid}/nudges").json()
    assert [n["id"] for n in second] == [n["id"] for n in first]
    assert published == []  # no republish on a same-day refresh


def test_ws_receives_nudge_created_on_first_generation(client, space_id):
    install_fake()
    sid = create_session(client, space_id, "ravi")

    with client.websocket_connect(f"/ws/{space_id}") as ws:
        first = client.get(f"/api/customer/{sid}/nudges").json()
        events = [ws.receive_json() for _ in first]
        assert all(e["type"] == "nudge.created" for e in events)
        assert {e["payload"]["id"] for e in events} == {n["id"] for n in first}


def test_two_personas_in_the_same_space_get_independent_feeds(client, space_id):
    install_fake()
    sid_ravi = create_session(client, space_id, "ravi")
    sid_vikram = create_session(client, space_id, "vikram")

    ravi_feed = client.get(f"/api/customer/{sid_ravi}/nudges").json()
    vikram_feed = client.get(f"/api/customer/{sid_vikram}/nudges").json()

    assert all(n["persona_id"] == "ravi" for n in ravi_feed)
    assert all(n["persona_id"] == "vikram" for n in vikram_feed)
    assert not any(n["intent"] in ("opportunity", "contextual") for n in vikram_feed if n["kind"] == "functional")
