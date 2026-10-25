
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200


def test_workflow_rejects_empty_question():
    response = client.post(
        "/workflow",
        json={"question": ""}
    )

    assert response.status_code == 422
