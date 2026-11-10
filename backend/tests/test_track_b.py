"""Tests for Track B: external API helper, alert rules and the risk model.

Run from the project root with:
    python -m pytest backend/tests/test_track_b.py -v
"""

from unittest.mock import patch

import pytest

from backend.services.http_client import ExternalAPIError, get_json
from backend.services.api_services import search_health_information
from backend.wellness import alerts
from backend.wellness.ml_risk import predict_risk_from_features, RISK_LABELS


# ---------- 1. External API helper ----------

class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_get_json_returns_payload():
    with patch("backend.services.http_client.requests.get",
               return_value=FakeResponse(200, {"ok": True})):
        assert get_json("Test", "http://example.com") == {"ok": True}


def test_get_json_404_raises_readable_error():
    with patch("backend.services.http_client.requests.get",
               return_value=FakeResponse(404)):
        with pytest.raises(ExternalAPIError) as err:
            get_json("Test", "http://example.com")
    assert "not found" in err.value.message


def test_nlm_flattens_nested_names():
    payload = ["diabetes", 1, None, [["Diabetes Mellitus"], ["Diabetes Insipidus"]]]
    with patch("backend.services.http_client.requests.get",
               return_value=FakeResponse(200, payload)):
        result = search_health_information("diabetes")
    assert result["results"] == ["Diabetes Mellitus", "Diabetes Insipidus"]


def test_empty_query_is_rejected_without_calling_network():
    with patch("backend.services.http_client.requests.get") as mocked:
        with pytest.raises(ExternalAPIError):
            search_health_information("   ")
        mocked.assert_not_called()


# ---------- 2. Alert rules ----------

@pytest.fixture
def saved_alerts(monkeypatch):
    """Capture alerts instead of writing to the real database."""
    saved = []
    monkeypatch.setattr(
        alerts, "_save_alert",
        lambda user_id, name, severity, message, number: saved.append(name) or {"rule": name},
    )
    return saved


def test_high_blood_sugar_creates_alert(saved_alerts):
    alerts.check_reading(1, "blood_sugar", "300")
    assert "blood_sugar" in saved_alerts


def test_normal_blood_sugar_creates_no_alert(saved_alerts):
    alerts.check_reading(1, "blood_sugar", "110")
    assert saved_alerts == []


def test_low_spo2_is_urgent(saved_alerts):
    alerts.check_reading(1, "spo2", "88")
    assert "spo2" in saved_alerts


# ---------- 3. Risk model ----------

def test_risk_model_returns_valid_label_and_probabilities():
    features = {
        "adherence_percent": 60.0,
        "avg_blood_sugar": 180.0,
        "avg_systolic_bp": 150.0,
        "avg_sleep_hours": 5.5,
        "avg_steps": 2000,
    }
    result = predict_risk_from_features(features)
    assert result["risk_label"] in RISK_LABELS
    assert abs(sum(result["probabilities"].values()) - 1.0) < 0.01
    assert 0.0 <= result["risk_score"] <= 1.0