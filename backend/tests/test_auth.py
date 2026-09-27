import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_register_and_login():
    email = "testuser@example.com"
    password = "secretpassword"

    # Register
    res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert res.status_code in [200, 400] # 400 if user exists from previous run

    # Login
    res = client.post("/api/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Get profile
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == email
