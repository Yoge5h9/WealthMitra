"""GET /api/customer/{session_id}/summary, GET /api/audit/{session_id}."""

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


def create_session(client, space_id, persona_id) -> str:
    response = client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": persona_id})
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_summary_shape_external_hidden_before_aa_connect(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "ravi")

    response = client.get(f"/api/customer/{sid}/summary")
    assert response.status_code == 200
    data = response.json()

    assert set(data) == {"profile", "metrics", "holdings", "goals"}
    assert data["profile"]["name"] == "Ravi Sharma"
    metrics = data["metrics"]
    for key in ("net_worth", "monthly_income", "monthly_surplus", "idle_balance",
                "spend_by_category", "risk_band", "segment", "goal_progress"):
        assert key in metrics

    assert data["holdings"]["aa_connected"] is False
    assert data["holdings"]["external"] == []
    assert data["holdings"]["external_liabilities"] == []


def test_summary_reveals_external_holdings_once_aa_connected(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "ravi")

    client.post("/api/aa/consent", json={"session_id": sid, "step": "transfer", "granted": True})
    client.post("/api/aa/consent", json={"session_id": sid, "step": "processing", "granted": True})

    data = client.get(f"/api/customer/{sid}/summary").json()
    assert data["holdings"]["aa_connected"] is True
    assert len(data["holdings"]["external"]) == 2


def test_summary_unknown_session_404(client):
    assert client.get("/api/customer/sess_ghost/summary").status_code == 404


def test_audit_returns_session_entries_in_order(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "ravi")

    install_fake([resp(text="All good.")])
    client.post("/api/chat", json={"session_id": sid, "message": "hello there"})

    response = client.get(f"/api/audit/{sid}")
    assert response.status_code == 200
    entries = response.json()
    assert entries
    assert all(e["session_id"] == sid for e in entries)
    kinds = {e["kind"] for e in entries}
    assert "routing" in kinds
    assert "llm_call" in kinds


def test_audit_unknown_session_404(client):
    assert client.get("/api/audit/sess_ghost").status_code == 404


def test_rm_summary_by_persona_matches_session_summary(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id, "ravi")

    by_session = client.get(f"/api/customer/{sid}/summary")
    by_persona = client.get(f"/api/spaces/{space_id}/customers/ravi/summary")
    assert by_persona.status_code == 200
    assert by_persona.json() == by_session.json()


def test_rm_summary_unknown_persona_404(client, space_id):
    response = client.get(f"/api/spaces/{space_id}/customers/nobody/summary")
    assert response.status_code == 404


def test_rm_summary_unknown_space_404(client):
    response = client.get("/api/spaces/sp_missing/customers/ravi/summary")
    assert response.status_code == 404
