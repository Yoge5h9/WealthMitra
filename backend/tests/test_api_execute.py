"""POST /api/execute: drives a real chat turn through
request_execution to get a genuine confirm_token, then exercises the
execute endpoint's compliance/idempotency/cap rules against it.
"""

import json

import pytest
from agent_fakes import FakeGateway, call, resp
from fastapi.testclient import TestClient

from app.agent import set_orchestrator
from app.agent.orchestrator import Orchestrator
from app.catalogue import eligible_shelf
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


def create_session(client, space_id, persona_id="ravi") -> str:
    response = client.post(f"/api/spaces/{space_id}/sessions", json={"persona_id": persona_id})
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def prepare_confirm(client, space_id) -> dict:
    """Runs a real auto_execute turn for ravi and returns the execution_confirm card."""
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id)

    product = next(
        p for p in eligible_shelf("mass_retail_salaried", "moderate", monthly_surplus=20862.0) if p.tag == "vanilla"
    )
    install_fake([
        resp(tool_calls=[call("request_execution", {"product_id": product.id, "amount": 5000})]),
        resp(text=f"I can set up {product.name} for ₹5,000. Confirm below."),
    ])
    response = client.post("/api/chat", json={"session_id": sid, "message": "I want to invest my surplus"})
    assert response.status_code == 200
    frames = sse_frames(response.text)
    confirm = next(f["card"] for f in frames if f["type"] == "card" and f["card"]["card_type"] == "execution_confirm")
    return {"session_id": sid, "product_id": confirm["product_id"], "amount": confirm["amount"],
            "confirm_token": confirm["confirm_token"]}


def test_execute_returns_receipt_and_publishes_event(client, space_id):
    confirm = prepare_confirm(client, space_id)

    with client.websocket_connect(f"/ws/{space_id}") as ws:
        response = client.post("/api/execute", json=confirm)
        assert response.status_code == 200, response.text
        receipt = response.json()
        assert receipt["session_id"] == confirm["session_id"]
        assert receipt["product_id"] == confirm["product_id"]
        assert receipt["amount"] == confirm["amount"]
        assert receipt["receipt_id"]
        assert receipt["audit_ref"].startswith("aud_")

        event = ws.receive_json()
        assert event["type"] == "execution.completed"
        assert event["payload"]["receipt_id"] == receipt["receipt_id"]

    space = get_space_store().get(space_id)
    persona_id = space.sessions[confirm["session_id"]]["persona_id"]
    assert space.portfolios[persona_id][0]["product_id"] == confirm["product_id"]
    exec_entries = [e for e in space.audit if e.kind == "execution"]
    assert len(exec_entries) == 1


def test_execute_is_idempotent_per_confirm_token(client, space_id):
    confirm = prepare_confirm(client, space_id)

    first = client.post("/api/execute", json=confirm).json()
    second = client.post("/api/execute", json=confirm).json()
    assert first == second

    space = get_space_store().get(space_id)
    persona_id = space.sessions[confirm["session_id"]]["persona_id"]
    assert len(space.portfolios[persona_id]) == 1  # replay never double-books
    assert len([e for e in space.audit if e.kind == "execution"]) == 1
    assert confirm["confirm_token"] in space.receipts  # receipt lives on the space


def test_execute_replay_after_reset_is_rejected(client, space_id):
    confirm = prepare_confirm(client, space_id)
    assert client.post("/api/execute", json=confirm).status_code == 200

    assert client.post(f"/api/spaces/{space_id}/reset").status_code == 200

    # The reset discarded the session (and the receipt registry with it): a
    # stale confirm token must never replay a stale 200 into the fresh space.
    response = client.post("/api/execute", json=confirm)
    assert response.status_code == 404

    space = get_space_store().get(space_id)
    assert space.receipts == {}
    assert space.portfolios == {}


def test_execute_regulated_product_403_even_with_fabricated_token(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id)
    response = client.post("/api/execute", json={
        "session_id": sid, "product_id": "flexicap_mf", "amount": 5000, "confirm_token": "cfm_fabricated",
    })
    assert response.status_code == 403
    assert response.json() == {"detail": "regulated_product_requires_rm"}


def test_execute_amount_above_cap_400(client, space_id):
    confirm = prepare_confirm(client, space_id)
    response = client.post("/api/execute", json={**confirm, "amount": 10_00_00_001})
    assert response.status_code == 400


def test_execute_invalid_confirm_token_400(client, space_id):
    confirm = prepare_confirm(client, space_id)
    response = client.post("/api/execute", json={**confirm, "confirm_token": "cfm_wrong"})
    assert response.status_code == 400


def test_execute_unknown_product_404(client, space_id):
    install_fake([resp(text="Hello!")])
    sid = create_session(client, space_id)
    response = client.post("/api/execute", json={
        "session_id": sid, "product_id": "ghost_product", "amount": 5000, "confirm_token": "cfm_x",
    })
    assert response.status_code == 404


def test_execute_unknown_session_404(client):
    response = client.post("/api/execute", json={
        "session_id": "sess_ghost", "product_id": "fd_ladder", "amount": 5000, "confirm_token": "cfm_x",
    })
    assert response.status_code == 404
