import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
)
def test_vite_development_origins_are_allowed(origin):
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] == origin


def test_unrelated_origin_is_not_allowed():
    response = client.options(
        "/health",
        headers={
            "Origin": "https://unrelated.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
