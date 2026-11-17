from app.models import Student


def register_student(client):
    """Create a student account for authentication tests."""
    return client.post(
        "/register",
        data={
            "student_id": "S12345",
            "full_name": "A Student",
            "email": "student@example.com",
            "password": "securepass",
        },
    )


def test_valid_credentials_grant_access_to_dashboard(client):
    register_student(client)

    response = client.post(
        "/login",
        data={"identifier": "S12345", "password": "securepass"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Student Dashboard" in response.data
    assert b"Welcome, A Student." in response.data


def test_invalid_credentials_show_error_without_authenticating(client, app):
    register_student(client)

    response = client.post(
        "/login",
        data={"identifier": "S12345", "password": "incorrect"},
        follow_redirects=True,
    )

    assert b"Invalid student ID/email or password." in response.data
    with client.session_transaction() as session:
        assert "student_id" not in session
    with app.app_context():
        assert Student.query.count() == 1


def test_dashboard_redirects_unauthenticated_student_to_login(client):
    response = client.get("/dashboard", follow_redirects=True)

    assert response.status_code == 200
    assert b"Please log in to access that page." in response.data
    assert b"Student Dashboard" not in response.data


def test_logout_terminates_access_to_protected_dashboard(client):
    register_student(client)
    client.post(
        "/login",
        data={"identifier": "S12345", "password": "securepass"},
    )

    response = client.post("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"You are logged out." in response.data
    with client.session_transaction() as session:
        assert "student_id" not in session

    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in to access that page." in response.data
    assert b"Student Dashboard" not in response.data


def test_logout_does_not_change_session_on_get(client):
    register_student(client)
    client.post(
        "/login",
        data={"identifier": "S12345", "password": "securepass"},
    )

    response = client.get("/logout")

    assert response.status_code == 405
    with client.session_transaction() as session:
        assert session.get("student_id") is not None
