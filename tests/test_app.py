"""Хелсчек, раздача фронтенда, SPA-fallback и формат ошибок фреймворка."""

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_head_on_existing_api_route(client: TestClient) -> None:
    get = client.get("/api/cities")
    head = client.head("/api/cities")
    assert head.status_code == 200
    assert head.headers["content-type"] == get.headers["content-type"]
    assert head.content == b""


def test_head_on_frontend_route(client: TestClient) -> None:
    response = client.head("/lookup")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_spa_fallback_serves_index_on_direct_links(client: TestClient) -> None:
    for path in ("/", "/lookup", "/booking/MOWLED-20260101-1"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html")
        assert "id='root'" in response.text


def test_static_file_served_with_own_type(client: TestClient) -> None:
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "asset" in response.text


def test_path_traversal_does_not_leave_public_dir(client: TestClient) -> None:
    response = client.get("/..%2Fsecret.txt")
    assert response.status_code == 200
    assert "secret" not in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_unknown_api_path_returns_json_404(client: TestClient) -> None:
    response = client.get("/api/unknown")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["code"] == "not_found"
    assert response.json()["message"]


def test_unsupported_method_returns_json_error(client: TestClient) -> None:
    response = client.delete("/")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
