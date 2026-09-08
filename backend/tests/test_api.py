"""API endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "PC Assistant API" in response.json()["name"]

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat():
    response = client.post("/api/chat/", json={"message": "Hello"})
    assert response.status_code == 200

def test_system_info():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    assert "cpu_percent" in response.json()
