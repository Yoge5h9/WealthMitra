"""GET /api/spaces/{space}/leads, POST /api/leads/{lead_id}/status."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.spaces import get_space_store
from app.domain.models import LeadPacket
from app.main import create_app

_NOW = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def space_id() -> str:
    return get_space_store().create_space()


def _lead(lead_id: str, priority: int, status: str = "new") -> LeadPacket:
    return LeadPacket(
        lead_id=lead_id,
        family="investment_insurance",
        status=status,
        customer={"persona_id": "ravi", "name": "Ravi Sharma", "segment": "mass_retail_salaried",
                  "age_band": "25-34", "city_tier": "urban_t1", "language": "en"},
        trigger={"type": "chat_message", "utterance": "x", "ts": _NOW.isoformat()},
        financial_snapshot={"monthly_income": 0, "monthly_surplus": 0, "idle_balance": 0,
                             "external_holdings": [], "liabilities": []},
        risk={"capacity_score": 50, "tolerance_score": 50, "band": "moderate"},
        goals=[],
        suitability={"recommended_shelf": [], "excluded": [], "reasons": []},
        next_best_action="RM to follow up.",
        consent={"aa_consent_id": None, "advice_consent": False},
        priority_score=priority,
        created_at=_NOW,
    )


def test_list_leads_sorted_by_priority_desc(client, space_id):
    space = get_space_store().get(space_id)
    space.leads.append(_lead("LP-2026-000001", priority=10))
    space.leads.append(_lead("LP-2026-000002", priority=80))
    space.leads.append(_lead("LP-2026-000003", priority=45))

    response = client.get(f"/api/spaces/{space_id}/leads")
    assert response.status_code == 200
    ids = [lead["lead_id"] for lead in response.json()]
    assert ids == ["LP-2026-000002", "LP-2026-000003", "LP-2026-000001"]


def test_list_leads_unknown_space_404(client):
    assert client.get("/api/spaces/nope/leads").status_code == 404


def test_update_lead_status_publishes_lead_updated(client, space_id):
    space = get_space_store().get(space_id)
    space.leads.append(_lead("LP-2026-000001", priority=50))

    with client.websocket_connect(f"/ws/{space_id}") as ws:
        response = client.post(
            f"/api/leads/LP-2026-000001/status", params={"space_id": space_id}, json={"status": "contacted"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "contacted"

        event = ws.receive_json()
        assert event["type"] == "lead.updated"
        assert event["payload"]["lead_id"] == "LP-2026-000001"
        assert event["payload"]["status"] == "contacted"

    assert get_space_store().get(space_id).leads[0].status == "contacted"


def test_update_lead_status_unknown_lead_404(client, space_id):
    response = client.post(
        "/api/leads/LP-2026-999999/status", params={"space_id": space_id}, json={"status": "contacted"}
    )
    assert response.status_code == 404


def test_update_lead_status_invalid_status_422(client, space_id):
    space = get_space_store().get(space_id)
    space.leads.append(_lead("LP-2026-000001", priority=50))
    response = client.post(
        "/api/leads/LP-2026-000001/status", params={"space_id": space_id}, json={"status": "bogus"}
    )
    assert response.status_code == 422


def test_update_lead_status_missing_space_id_422(client, space_id):
    space = get_space_store().get(space_id)
    space.leads.append(_lead("LP-2026-000001", priority=50))
    response = client.post("/api/leads/LP-2026-000001/status", json={"status": "contacted"})
    assert response.status_code == 422
