"""POST /api/aa/consent: the two-step consent state machine,
the refi lead it triggers exactly once, revocation, priya's "not available"
path, and consent flowing into a chat-built LeadPacket after connecting.
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


def create_session(client, space_id, persona_id) -> str:
    response = client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": persona_id})
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def consent(client, session_id, step, granted):
    return client.post("/api/aa/consent", json={"session_id": session_id, "step": step, "granted": granted})


def test_two_step_state_machine_only_connects_once_both_granted(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "vikram")

    r1 = consent(client, sid, "transfer", True)
    assert r1.status_code == 200
    state = r1.json()
    assert state == {"aa_available": True, "transfer_granted": True, "processing_granted": False,
                      "connected": False, "holdings": None}

    r2 = consent(client, sid, "processing", True)
    assert r2.status_code == 200
    state = r2.json()
    assert state["connected"] is True
    assert state["transfer_granted"] is True
    assert state["processing_granted"] is True
    assert state["holdings"] == []  # vikram has liabilities, no holdings

    space = get_space_store().get(space_id)
    assert space.personas["vikram"].external.connected is True


def test_connect_publishes_aa_connected_and_creates_refi_lead_once(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "vikram")  # 14% personal loan > 10.5% IDBI benchmark

    with client.websocket_connect(f"/ws/{space_id}") as ws:
        consent(client, sid, "transfer", True)
        consent(client, sid, "processing", True)

        events = [ws.receive_json(), ws.receive_json()]
        types = [e["type"] for e in events]
        assert "aa.connected" in types
        assert "lead.created" in types
        lead_event = next(e for e in events if e["type"] == "lead.created")
        assert lead_event["payload"]["family"] == "loans_cards"

    space = get_space_store().get(space_id)
    assert len(space.leads) == 1
    assert space.leads[0].family == "loans_cards"

    # Disconnect + reconnect must NOT create a second lead.
    consent(client, sid, "transfer", False)
    r = consent(client, sid, "transfer", True)
    assert r.json()["connected"] is True  # processing was never revoked
    assert len(get_space_store().get(space_id).leads) == 1


def test_revocation_hides_holdings_again(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "ravi")  # ravi has FD + NPS holdings, no high-rate liability
    consent(client, sid, "transfer", True)
    r = consent(client, sid, "processing", True)
    assert r.json()["connected"] is True
    assert len(r.json()["holdings"]) == 2

    r = consent(client, sid, "transfer", False)
    assert r.status_code == 200
    assert r.json()["connected"] is False
    assert r.json()["holdings"] is None
    assert get_space_store().get(space_id).personas["ravi"].external.connected is False

    # No refinanceable liability for ravi -> no lead ever created.
    assert get_space_store().get(space_id).leads == []


def test_priya_has_no_aa_returns_clean_not_available(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "priya")

    r = consent(client, sid, "transfer", True)
    assert r.status_code == 200
    assert r.json() == {"aa_available": False, "transfer_granted": False, "processing_granted": False,
                         "connected": False, "holdings": None}
    assert get_space_store().get(space_id).personas["priya"].external.connected is False


def test_consent_flows_into_lead_created_after_connect(client, space_id):
    # meera (affluent, cash-surplus, no liabilities, no distress flags) — a
    # clean regulated_query -> rm_lead turn with no AA-triggered refi lead to
    # confuse which lead the test is checking.
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "meera")

    consent(client, sid, "transfer", True)
    processing_state = consent(client, sid, "processing", True).json()
    assert processing_state["connected"] is True

    space = get_space_store().get(space_id)
    consent_id = space.sessions[sid]["aa_consent"]["consent_id"]
    assert consent_id is not None

    install_fake([resp(text="A specialist will reach out shortly.")])
    response = client.post("/api/chat", json={"session_id": sid, "message": "I want mutual funds"})
    assert response.status_code == 200
    frames = sse_frames(response.text)
    card = next(f["card"] for f in frames if f["type"] == "card" and f["card"]["card_type"] == "routed_to_rm")

    chat_lead = next(lead for lead in space.leads if lead.lead_id == card["lead_id"])
    assert chat_lead.consent == {"aa_consent_id": consent_id, "advice_consent": True}


def test_unknown_session_404(client):
    r = consent(client, "sess_ghost", "transfer", True)
    assert r.status_code == 404
