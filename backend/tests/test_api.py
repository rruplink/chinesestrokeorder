from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["deepseekConfigured"] in {"yes", "no"}
    assert payload["strokeDataCdn"] in {"enabled", "disabled"}


def test_preview_endpoint_returns_cards_and_cost():
    response = client.post(
        "/api/preview",
        json={"deckName": "Test Deck", "lines": ["你好", "", "中国"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["cost"]["detectedCards"] == 2
    assert payload["cards"][0]["hanzi"] == "你好"
    assert payload["cards"][0]["needsAiLookup"] is False


def test_preview_rejects_more_than_250_cards():
    response = client.post(
        "/api/preview",
        json={"deckName": "Too Big", "lines": [str(index) for index in range(251)]},
    )
    assert response.status_code == 422
    assert "1-250" in response.json()["detail"]


def test_generate_endpoint_returns_apkg():
    response = client.post(
        "/api/generate",
        json={"deckName": "Test Deck", "lines": ["你好"]},
    )
    assert response.status_code == 200
    assert 'filename="Test_Deck.apkg"' in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")
