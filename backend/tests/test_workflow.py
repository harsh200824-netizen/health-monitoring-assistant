
from fastapi.testclient import TestClient
from backend.main import app, get_current_user

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_workflow_rejects_empty_question():
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "test-user",
        "role": "patient"
    }

    try:
        response = client.post(
            "/workflow",
            json={"question": ""}
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
