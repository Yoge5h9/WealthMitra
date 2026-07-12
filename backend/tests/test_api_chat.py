"""Sessions + chat API tests: session creation with a grounded greeting, SSE
frame stream, language toggle, and 404 paths.

The orchestrator singleton is swapped for one driven by a scripted fake
gateway, so no real LLM is ever invoked.
"""

import json
from datetime import datetime, timezone

import pytest
from agent_fakes import FakeGateway, call, resp
from fastapi.testclient import TestClient

from app.agent import set_orchestrator
from app.agent.orchestrator import Orchestrator
from app.core.spaces import get_space_store
from app.main import create_app

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)


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
    set_orchestrator(Orchestrator(fake, now=lambda: _NOW))
    return fake


def sse_frames(text: str) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in text.splitlines() if line.startswith("data: ")]


def create_session(client, space_id, persona_id="ravi", language=None) -> dict:
    body = {"persona_id": persona_id}
    if language:
        body["language"] = language
    response = client.post(f"/api/spaces/{space_id}/sessions", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_create_session_returns_greeting_frames(client, space_id):
    install_boom()  # greeting is deterministic — session open must never hit the LLM
    data = create_session(client, space_id)
    assert data["session_id"].startswith("sess_")
    kinds = [f["type"] for f in data["greeting"]]
    assert kinds[0] == "avatar" and kinds[-1] == "done"
    assert "error" not in data["greeting"][-1]
    text = "".join(f["text"] for f in data["greeting"] if f["type"] == "token")
    assert "Ravi" in text
    card_frames = [f for f in data["greeting"] if f["type"] == "card"]
    assert card_frames[0]["card"]["card_type"] == "spend_summary"


def test_session_language_defaults_to_persona(client, space_id):
    install_fake([resp(text="Namaste!")])
    data = create_session(client, space_id, persona_id="shanta")  # shanta is hi
    space = get_space_store().get(space_id)
    assert space.sessions[data["session_id"]]["language"] == "hi"


def test_session_default_space_works(client):
    install_fake([resp(text="Hello!")])
    data = create_session(client, "default")
    assert data["session_id"].startswith("sess_")


def test_new_to_idbi_profile_flow_is_deterministic_and_never_calls_the_llm(client, space_id):
    install_boom()
    data = create_session(client, space_id, persona_id="new_to_idbi")
    first_card = next(frame["card"] for frame in data["greeting"] if frame["type"] == "card")
    assert first_card["card_type"] == "profile_question"
    assert first_card["step"] == 1

    answers = ["Save safely", "Salaried", "₹5,000–₹25,000", "Safety first"]
    frames: list[dict] = []
    for answer in answers:
        response = client.post("/api/chat", json={"session_id": data["session_id"], "message": answer})
        assert response.status_code == 200
        frames = sse_frames(response.text)
        assert frames[-1]["type"] == "done"
        assert "error" not in frames[-1]

    summary = next(frame["card"] for frame in frames if frame["type"] == "card")
    assert summary["card_type"] == "profile_summary"
    assert summary["answers"]["income"] == "Salaried"
    assert any(frame.get("card", {}).get("card_type") == "aa_connect" for frame in frames)

    consent = client.post("/api/aa/consent", json={"session_id": data["session_id"], "step": "transfer", "granted": True})
    assert consent.status_code == 200 and consent.json()["connected"] is False
    consent = client.post("/api/aa/consent", json={"session_id": data["session_id"], "step": "processing", "granted": True})
    assert consent.status_code == 200 and consent.json()["connected"] is True
    assert consent.json()["holdings"] == []

    resumed = create_session(client, space_id, persona_id="new_to_idbi")
    resumed_card = next(frame["card"] for frame in resumed["greeting"] if frame["type"] == "card")
    assert resumed_card["card_type"] == "profile_summary"
    assert resumed_card["answers"]["priority"] == "Save safely"


def test_unknown_space_404(client):
    install_fake([])
    assert client.post("/api/spaces/nope/sessions", json={"persona_id": "ravi"}).status_code == 404


def test_unknown_persona_404(client, space_id):
    install_fake([])
    assert client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": "ghost"}).status_code == 404


def test_invalid_language_422(client, space_id):
    install_fake([])
    response = client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": "ravi", "language": "fr"})
    assert response.status_code == 422


def test_chat_streams_sse_frames_in_order(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id)["session_id"]

    install_fake([
        resp(tool_calls=[call("get_spend_summary")]),
        resp(text="Your monthly income is ₹85,000."),
    ])
    response = client.post("/api/chat", json={"session_id": sid, "message": "how is my spending?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    frames = sse_frames(response.text)
    kinds = [f["type"] for f in frames]
    assert kinds[0] == "avatar"
    assert kinds[-1] == "done"
    first_token = kinds.index("token")
    first_card = kinds.index("card")
    assert first_token < first_card < kinds.index("done")
    assert "".join(f["text"] for f in frames if f["type"] == "token") == "Your monthly income is ₹85,000."
    assert frames[-1]["audit_ref"].startswith("aud_")


def test_chat_language_toggle_mid_session(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, language="en")["session_id"]

    fake = install_fake([resp(text="आपकी आय अच्छी है।")])
    response = client.post("/api/chat", json={"session_id": sid, "message": "मेरा खर्च?", "language": "hi"})
    assert response.status_code == 200
    assert get_space_store().get(space_id).sessions[sid]["language"] == "hi"
    assert "Hindi" in fake.requests[0].messages[0].content


def test_chat_unknown_session_404(client):
    install_fake([])
    assert client.post("/api/chat", json={"session_id": "sess_ghost", "message": "hi"}).status_code == 404


class BoomGateway:
    """A gateway whose every call explodes — drives the failure paths."""

    provider_name = "boom"

    def complete(self, req):
        raise RuntimeError("provider exploded")

    def stream(self, req):
        raise RuntimeError("provider exploded")


def install_boom() -> None:
    set_orchestrator(Orchestrator(BoomGateway(), now=lambda: _NOW))


def test_chat_stream_always_closes_with_done_on_failure(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id)["session_id"]

    install_boom()
    response = client.post("/api/chat", json={"session_id": sid, "message": "how is my spending?"})
    assert response.status_code == 200
    frames = sse_frames(response.text)
    assert frames, "stream must not be empty"
    assert frames[-1]["type"] == "done"
    assert frames[-1]["error"] is True
    assert frames[-1]["audit_ref"].startswith("aud_")
    space = get_space_store().get(space_id)
    failures = [e for e in space.audit if e.kind == "guardrail" and e.name == "turn_failed"]
    assert failures and failures[-1].session_id == sid


def test_greeting_is_audited_and_session_usable(client, space_id):
    install_boom()
    data = create_session(client, space_id)  # deterministic greeting, no LLM

    install_fake([resp(text="Welcome back!")])
    response = client.post("/api/chat", json={"session_id": data["session_id"], "message": "hello"})
    assert response.status_code == 200
    chat_frames = sse_frames(response.text)
    assert chat_frames[-1]["type"] == "done"
    assert "error" not in chat_frames[-1]
    space = get_space_store().get(space_id)
    greetings = [e for e in space.audit if e.kind == "guardrail" and e.name == "greeting_static"]
    assert greetings and greetings[-1].session_id == data["session_id"]


def test_chat_rm_lead_flow_end_to_end(client, space_id):
    install_fake([resp(text="Hello Meera!")])
    sid = create_session(client, space_id, persona_id="meera", language="gu")["session_id"]

    install_fake([resp(text="A specialist will reach out shortly.")])
    response = client.post("/api/chat", json={"session_id": sid, "message": "I want equity mutual funds"})
    frames = sse_frames(response.text)
    card = next(f["card"] for f in frames if f["type"] == "card")
    assert card["card_type"] == "routed_to_rm"

    space = get_space_store().get(space_id)
    assert len(space.leads) == 1
    assert space.leads[0].lead_id == card["lead_id"]
