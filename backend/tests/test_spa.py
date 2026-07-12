from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_root_shows_build_pending_when_dist_missing(tmp_path: Path) -> None:
    client = TestClient(create_app(frontend_dist=tmp_path / "does-not-exist"))

    response = client.get("/")

    assert response.status_code == 200
    assert "frontend build pending" in response.text


def test_api_routes_unaffected_when_dist_missing(tmp_path: Path) -> None:
    client = TestClient(create_app(frontend_dist=tmp_path / "does-not-exist"))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_index_when_dist_present(built_dist: Path) -> None:
    client = TestClient(create_app(frontend_dist=built_dist))

    response = client.get("/")

    assert response.status_code == 200
    assert "WealthMitra SPA" in response.text


def test_unknown_route_falls_back_to_index_when_dist_present(built_dist: Path) -> None:
    client = TestClient(create_app(frontend_dist=built_dist))

    response = client.get("/dashboard/net-worth")

    assert response.status_code == 200
    assert "WealthMitra SPA" in response.text


def test_real_static_asset_is_served_when_dist_present(built_dist: Path) -> None:
    client = TestClient(create_app(frontend_dist=built_dist))

    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_api_routes_unaffected_when_dist_present(built_dist: Path) -> None:
    client = TestClient(create_app(frontend_dist=built_dist))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
