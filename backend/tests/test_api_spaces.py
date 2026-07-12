"""POST /api/spaces, POST /api/spaces/{space}/reset, GET /api/personas."""

import pytest
from fastapi.testclient import TestClient

from app.core.spaces import get_space_store
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_create_space_returns_space_id(client):
    response = client.post("/api/spaces")
    assert response.status_code == 200
    space_id = response.json()["space_id"]
    assert get_space_store().get(space_id) is not None


def test_create_space_twice_yields_distinct_spaces(client):
    a = client.post("/api/spaces").json()["space_id"]
    b = client.post("/api/spaces").json()["space_id"]
    assert a != b


def test_reset_restores_pristine_state_and_leaves_other_space_untouched(client):
    space_id = client.post("/api/spaces").json()["space_id"]
    other_id = client.post("/api/spaces").json()["space_id"]

    space = get_space_store().get(space_id)
    space.personas["ravi"].profile.name = "Mutated Name"
    other = get_space_store().get(other_id)
    other.personas["ravi"].profile.name = "Other Mutated Name"

    response = client.post(f"/api/spaces/{space_id}/reset")
    assert response.status_code == 200
    assert response.json() == {"space_id": space_id, "reset": True}

    reset_space = get_space_store().get(space_id)
    assert reset_space.personas["ravi"].profile.name == "Ravi Sharma"
    assert reset_space.leads == []

    untouched = get_space_store().get(other_id)
    assert untouched.personas["ravi"].profile.name == "Other Mutated Name"


def test_reset_unknown_space_404(client):
    assert client.post("/api/spaces/does-not-exist/reset").status_code == 404


def test_reset_default_space_works_even_if_never_touched(client):
    response = client.post("/api/spaces/default/reset")
    assert response.status_code == 200


def test_list_personas_returns_roster_cards(client):
    response = client.get("/api/personas")
    assert response.status_code == 200
    personas = response.json()
    ids = {p["id"] for p in personas}
    assert {"ravi", "meera", "priya", "vikram"}.issubset(ids)

    ravi = next(p for p in personas if p["id"] == "ravi")
    assert set(ravi) == {"id", "name", "age", "city", "segment", "language", "avatar", "story"}
    assert ravi["name"] == "Ravi Sharma"
