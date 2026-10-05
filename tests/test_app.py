import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def activities_data():
    return {
        "Chess Club": {
            "description": "Test club",
            "schedule": "Fridays",
            "max_participants": 3,
            "participants": ["existing@example.com"],
        }
    }


@pytest.fixture
def client(monkeypatch, activities_data):
    monkeypatch.setattr(app_module, "activities", activities_data)
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_get_activities_returns_data_without_cache(client, activities_data):
    # Arrange
    expected_activities = activities_data

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_activities
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant_and_reduces_available_spots(
    client, activities_data
):
    # Arrange
    activity_name = "Chess Club"
    email = "new@example.com"
    activity = activities_data[activity_name]
    initial_spots = activity["max_participants"] - len(activity["participants"])

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    updated_activities = client.get("/activities").json()

    # Assert
    assert signup_response.status_code == 200
    assert signup_response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    updated_activity = updated_activities[activity_name]
    assert email in updated_activity["participants"]
    available_spots = (
        updated_activity["max_participants"] - len(updated_activity["participants"])
    )
    assert available_spots == initial_spots - 1


def test_signup_rejects_duplicate_participant(client, activities_data):
    # Arrange
    activity_name = "Chess Club"
    email = activities_data[activity_name]["participants"][0]
    initial_participant_count = len(activities_data[activity_name]["participants"])

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    updated_activity = client.get("/activities").json()[activity_name]

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert len(updated_activity["participants"]) == initial_participant_count
    assert updated_activity["participants"].count(email) == 1


def test_signup_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "student@example.com"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant(client, activities_data):
    # Arrange
    activity_name = "Chess Club"
    email = activities_data[activity_name]["participants"][0]
    initial_spots = (
        activities_data[activity_name]["max_participants"]
        - len(activities_data[activity_name]["participants"])
    )

    # Act
    unregister_response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    updated_activity = client.get("/activities").json()[activity_name]

    # Assert
    assert unregister_response.status_code == 200
    assert unregister_response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    assert email not in updated_activity["participants"]
    available_spots = (
        updated_activity["max_participants"] - len(updated_activity["participants"])
    )
    assert available_spots == initial_spots + 1


def test_unregister_returns_404_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": "student@example.com"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_returns_404_for_unregistered_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "absent@example.com"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"