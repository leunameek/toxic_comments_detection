"""Unit tests for the classifier service and classify endpoint."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services import classifier


PLAYER_KEY = "player-dev-key-1"
MODERATOR_KEY = "moderator-dev-key-1"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- ToxicPipeline._action unit tests (thresholds live in the pipeline object) ---

def test_pipeline_action_thresholds():
    from pipeline import ToxicPipeline
    import numpy as np

    # Build a minimal ToxicPipeline with known thresholds
    mock_clf = MagicMock()
    mock_clf.calibrated_classifiers_ = [MagicMock(estimator=MagicMock(coef_=np.zeros((1, 2))))]
    p = ToxicPipeline(
        vectorizer=MagicMock(),
        classifier=mock_clf,
        t_star=0.50,
        t_review=0.40,
        t_block=0.90,
        feature_names=np.array([]),
    )

    assert p._action(0.10) == "APPROVE"
    assert p._action(0.39) == "APPROVE"
    assert p._action(0.40) == "REVIEW"
    assert p._action(0.49) == "REVIEW"
    assert p._action(0.50) == "TOXIC_ALERT"
    assert p._action(0.89) == "TOXIC_ALERT"
    assert p._action(0.90) == "BLOCK"
    assert p._action(1.00) == "BLOCK"


# --- Endpoint tests (model mocked) ---

@pytest.fixture(autouse=True)
def mock_model():
    """Mock the ToxicPipeline so tests don't require the real model file."""
    mock_pipeline = MagicMock()
    mock_pipeline.predict_one.return_value = {
        "label": 1,
        "score": 0.87,
        "action": "TOXIC_ALERT",
        "top_features": ["noob", "terrible"],
    }

    with patch.object(classifier, "_pipeline", mock_pipeline):
        yield mock_pipeline


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["model_loaded"] is True


def test_classify_returns_result(client):
    resp = client.post(
        "/api/v1/classify",
        json={
            "message_id": "test-msg-001",
            "user_id": "user-test-001",
            "session_id": "session-test-001",
            "text": "eres un noob terrible",
        },
        headers={"X-API-Key": PLAYER_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["label"] == 1
    assert data["data"]["action"] == "TOXIC_ALERT"


def test_classify_idempotent(client):
    payload = {
        "message_id": "test-msg-idem",
        "user_id": "user-test-002",
        "session_id": "session-test-001",
        "text": "gg easy",
    }
    r1 = client.post("/api/v1/classify", json=payload, headers={"X-API-Key": PLAYER_KEY})
    r2 = client.post("/api/v1/classify", json=payload, headers={"X-API-Key": PLAYER_KEY})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["data"]["message_id"] == r2.json()["data"]["message_id"]


def test_classify_unauthorized(client):
    resp = client.post(
        "/api/v1/classify",
        json={"message_id": "x", "user_id": "u", "session_id": "s", "text": "hello"},
    )
    assert resp.status_code == 401


def test_classify_batch(client):
    resp = client.post(
        "/api/v1/classify/batch",
        json={
            "messages": [
                {"message_id": "b-001", "user_id": "u1", "session_id": "s1", "text": "gg"},
                {"message_id": "b-002", "user_id": "u2", "session_id": "s1", "text": "reportar"},
            ]
        },
        headers={"X-API-Key": PLAYER_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    assert len(data["results"]) == 2
