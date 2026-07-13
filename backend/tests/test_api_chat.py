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
from app.analytics import AnalyticsEngine
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
    assert len(consent.json()["holdings"]) == 2  # adaptive external MF + FD, revealed like every other persona

    resumed = create_session(client, space_id, persona_id="new_to_idbi")
    resumed_card = next(frame["card"] for frame in resumed["greeting"] if frame["type"] == "card")
    assert resumed_card["card_type"] == "profile_summary"
    assert resumed_card["answers"]["priority"] == "Save safely"


def complete_new_to_idbi_onboarding(
    client, space_id, answers=("Save safely", "Salaried", "₹5,000–₹25,000", "Safety first")
) -> str:
    """Drives a new_to_idbi session through all four onboarding questions
    (deterministic — no LLM) and returns the session id, ready for a normal
    chat turn."""
    install_boom()
    data = create_session(client, space_id, persona_id="new_to_idbi")
    for answer in answers:
        response = client.post("/api/chat", json={"session_id": data["session_id"], "message": answer})
        assert response.status_code == 200
    return data["session_id"]


def test_new_to_idbi_post_onboarding_turn_reaches_orchestrator(client, space_id):
    sid = complete_new_to_idbi_onboarding(client, space_id)
    space = get_space_store().get(space_id)
    assert "new_to_idbi" in space.personas

    install_fake([resp(text="Sure, here's what I can share.")])
    response = client.post("/api/chat", json={"session_id": sid, "message": "What can you help me with today?"})
    assert response.status_code == 200
    frames = sse_frames(response.text)
    assert frames[-1]["type"] == "done" and "error" not in frames[-1]
    text = "".join(f["text"] for f in frames if f["type"] == "token")
    assert "I remember your starting profile" not in text
    assert text == "Sure, here's what I can share."


def test_new_to_idbi_adaptive_portfolio_analytics_do_not_raise(client, space_id):
    """Salaried + mid surplus band ("₹5,000–₹25,000") — the synthetic ledger
    built from the four onboarding answers must behave like a real persona's:
    non-zero income/surplus, positive internal net worth, and a regular
    (not irregular) income signal, with external holdings still hidden until
    AA connects."""
    sid = complete_new_to_idbi_onboarding(client, space_id)
    space = get_space_store().get(space_id)

    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "new_to_idbi")}
    assert metrics["monthly_income"].value == 55000.0
    assert metrics["monthly_surplus"].value == 17500.0
    assert 5000.0 <= metrics["monthly_surplus"].value <= 25000.0
    assert metrics["net_worth"].value == {
        "internal": 105000.0, "external": 0.0, "total": 105000.0, "external_connected": False,
    }
    assert metrics["risk_band"].value in {"conservative", "moderate", "growth"}
    assert metrics["suitability_segment"].value == "mass_retail_salaried"
    assert metrics["behaviour_flags"].value == {"flags": ["salary_consistent"]}


def test_new_to_idbi_retired_income_recognised_as_pension(client, space_id):
    sid = complete_new_to_idbi_onboarding(
        client, space_id, answers=("Save safely", "Retired", "₹5,000–₹25,000", "Safety first")
    )
    space = get_space_store().get(space_id)

    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "new_to_idbi")}
    assert metrics["monthly_income"].value == 55000.0
    assert metrics["behaviour_flags"].value == {"flags": ["salary_consistent"]}
    # senior-age branch (age 65) takes priority over the default segment — expected.
    assert metrics["suitability_segment"].value == "senior"


def test_new_to_idbi_business_income_recognised_as_business_income(client, space_id):
    sid = complete_new_to_idbi_onboarding(
        client, space_id, answers=("Start investing", "Business or freelance", "₹5,000–₹25,000", "Balanced")
    )
    space = get_space_store().get(space_id)

    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "new_to_idbi")}
    assert metrics["monthly_income"].value == 55000.0
    assert metrics["behaviour_flags"].value == {"flags": ["salary_consistent"]}
    # At the mid surplus band the surplus ratio (~0.32) stays below the
    # cash_surplus_heavy threshold (0.4), so the "business" occupation keyword
    # alone does not flip the segment to "affluent" — deterministic and
    # intentional: only a genuinely cash-surplus-heavy business profile would.
    assert metrics["suitability_segment"].value == "mass_retail_salaried"


def test_new_to_idbi_aa_connect_reveals_holdings_and_grows_net_worth(client, space_id):
    sid = complete_new_to_idbi_onboarding(client, space_id)
    space = get_space_store().get(space_id)

    r = client.post("/api/aa/consent", json={"session_id": sid, "step": "transfer", "granted": True})
    assert r.json()["connected"] is False
    r = client.post("/api/aa/consent", json={"session_id": sid, "step": "processing", "granted": True})
    assert r.json()["connected"] is True
    assert len(r.json()["holdings"]) == 2
    assert space.personas["new_to_idbi"].external.connected is True

    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "new_to_idbi")}
    assert metrics["net_worth"].value["external"] > 0
    assert metrics["net_worth"].value["external_connected"] is True

    r = client.post("/api/aa/consent", json={"session_id": sid, "step": "transfer", "granted": False})
    assert r.json()["connected"] is False
    assert r.json()["holdings"] is None
    assert space.personas["new_to_idbi"].external.connected is False
    metrics = {m.id: m for m in AnalyticsEngine().compute(space, "new_to_idbi")}
    assert metrics["net_worth"].value["external"] == 0.0


def test_new_to_idbi_pre_onboarding_aa_consent_does_not_crash(client, space_id):
    install_boom()
    data = create_session(client, space_id, persona_id="new_to_idbi")  # no answers yet
    space = get_space_store().get(space_id)
    assert "new_to_idbi" not in space.personas

    r = client.post(
        "/api/aa/consent", json={"session_id": data["session_id"], "step": "transfer", "granted": True}
    )
    assert r.status_code == 200
    assert r.json() == {
        "aa_available": False, "transfer_granted": False, "processing_granted": False,
        "connected": False, "holdings": None,
    }


def test_new_to_idbi_summary_reflects_real_metrics_and_gates_external_on_consent(client, space_id):
    sid = complete_new_to_idbi_onboarding(client, space_id)

    before = client.get(f"/api/customer/{sid}/summary")
    assert before.status_code == 200
    body = before.json()
    assert body["metrics"]["monthly_income"] == 55000.0
    assert body["metrics"]["monthly_surplus"] == 17500.0
    assert body["holdings"]["aa_connected"] is False
    assert body["holdings"]["external"] == []

    client.post("/api/aa/consent", json={"session_id": sid, "step": "transfer", "granted": True})
    client.post("/api/aa/consent", json={"session_id": sid, "step": "processing", "granted": True})

    after = client.get(f"/api/customer/{sid}/summary").json()
    assert after["holdings"]["aa_connected"] is True
    assert len(after["holdings"]["external"]) == 2


def test_new_to_idbi_resume_injects_persona_for_orchestrator(client, space_id):
    complete_new_to_idbi_onboarding(client, space_id)
    space = get_space_store().get(space_id)
    assert space.new_customer_profile

    install_boom()  # resume greeting must stay deterministic
    resumed = create_session(client, space_id, persona_id="new_to_idbi")
    assert "new_to_idbi" in space.personas

    install_fake([resp(text="Happy to help.")])
    response = client.post("/api/chat", json={"session_id": resumed["session_id"], "message": "hello"})
    frames = sse_frames(response.text)
    text = "".join(f["text"] for f in frames if f["type"] == "token")
    assert text == "Happy to help."


def test_new_to_idbi_excluded_from_persona_roster(client):
    complete_new_to_idbi_onboarding(client, "default")
    ids = {p["id"] for p in client.get("/api/personas").json()}
    assert "new_to_idbi" not in ids
    assert "ravi" in ids


def test_new_to_idbi_regulated_request_routes_to_rm_never_auto_executes(client, space_id):
    sid = complete_new_to_idbi_onboarding(client, space_id)

    install_fake([resp(text="A specialist will reach out to you shortly.")])
    response = client.post("/api/chat", json={"session_id": sid, "message": "I want to invest in equity mutual funds"})
    frames = sse_frames(response.text)
    card = next(f["card"] for f in frames if f["type"] == "card")
    assert card["card_type"] == "routed_to_rm"

    space = get_space_store().get(space_id)
    assert len(space.leads) == 1
    assert space.leads[0].customer["persona_id"] == "new_to_idbi"


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
