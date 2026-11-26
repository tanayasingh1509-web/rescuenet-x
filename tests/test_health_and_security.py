#!/usr/bin/env python3
"""
Test Suite: Health AI Tier, Hardened Exception Handling, and Simulation Rate Limiting
Verifies:
1. GET /health includes 'ai_tier' ('gemini', 'ollama', or 'heuristic')
2. Setting GEMINI_API_KEY switches active ai_tier to 'gemini'
3. Global exception handler returns generic detail and request_id without exposing internal errors
4. Simulation rate limiter blocks excess requests with HTTP 429
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.security import simulation_limiter

def test_health_check_includes_ai_tier():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "ai_tier" in data
        assert data["ai_tier"] in ("gemini", "ollama", "heuristic")

def test_health_check_gemini_tier_activation(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_test_gemini_key_12345")
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ai_tier"] == "gemini"

def test_hardened_exception_handler():
    import json
    from unittest.mock import MagicMock
    from backend.main import global_exception_handler
    import asyncio

    mock_request = MagicMock()
    mock_request.state.request_id = "test-req-123"
    mock_request.method = "GET"
    mock_request.url.path = "/api/test"

    exc = RuntimeError("SecretDatabaseConnectionStringPasswordLeak")
    response = asyncio.run(global_exception_handler(mock_request, exc))
    assert response.status_code == 500
    body = json.loads(response.body.decode())
    assert body.get("detail") == "Internal server error"
    assert body.get("request_id") == "test-req-123"
    assert "SecretDatabaseConnectionStringPasswordLeak" not in response.body.decode()

def test_simulation_rate_limiter():
    with TestClient(app) as client:
        # Reset client tracking for test IP
        test_ip = "127.0.0.1"
        simulation_limiter._clients[test_ip] = []

        # Make requests up to limit
        for _ in range(simulation_limiter.max_requests):
            res = client.post("/api/simulate/scenario/flood")
            assert res.status_code == 200

        # Next request must be rejected with 429
        res = client.post("/api/simulate/scenario/flood")
        assert res.status_code == 429
        assert "Rate limit exceeded" in res.text

        # Reset limiter client tracking
        simulation_limiter._clients[test_ip] = []
