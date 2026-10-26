from fastapi.testclient import TestClient
from app.main import app
import pytest

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

SAMPLE = {
  "Area": 30000,
  "Perimeter": 600,
  "Major_Axis_Length": 250,
  "Minor_Axis_Length": 100,
  "Convex_Area": 30000,
  "Equiv_Diameter": 150,
  "Eccentricity": 1,
  "Solidity": 0.8,
  "Extent": 0.3,
  "Roundness": 0.3,
  "Aspect_Ration": 1,
  "Compactness": 0.3
}

def test_read_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_predict_returns_valid_probability(client):
    r = client.post("/predict", json=SAMPLE)
    assert r.status_code == 200

def test_predict_rejects_bad_input(client):
    bad = {**SAMPLE, "Area": -5}
    assert client.post("/predict", json=bad).status_code == 422

def test_explain_returns_factors(client):
    r = client.post("/explain", json=SAMPLE)
    assert r.status_code == 200
    assert len(r.json()["impactful features"]) > 4