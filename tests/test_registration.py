import pytest
from werkzeug.security import check_password_hash

from app.models import Student


def registration_data(**updates):
    data = {
        "student_id": "S12345",
        "full_name": "A Student",
        "email": "student@example.com",
        "password": "securepass",
    }
    data.update(updates)
    return data


def test_registration_creates_account_and_student_can_log_in(client, app):
    response = client.post("/register", data=registration_data())

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with app.app_context():
        student = Student.query.one()
        assert student.student_id == "S12345"
        assert student.full_name == "A Student"
        assert student.email == "student@example.com"

    response = client.post(
        "/login",
        data={"identifier": "S12345", "password": "securepass"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are logged in." in response.data
    with client.session_transaction() as session:
        assert session["student_id"] == student.id

    response = client.post(
        "/login",
        data={"identifier": "student@example.com", "password": "securepass"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are logged in." in response.data


@pytest.mark.parametrize("field", ["student_id", "full_name", "email", "password"])
def test_registration_rejects_missing_required_field(client, app, field):
    response = client.post(
        "/register",
        data=registration_data(**{field: ""}),
        follow_redirects=True,
    )

    assert b"All fields are required." in response.data
    with app.app_context():
        assert Student.query.count() == 0


def test_registration_rejects_malformed_email(client, app):
    response = client.post(
        "/register",
        data=registration_data(email="not-an-email"),
        follow_redirects=True,
    )

    assert b"Enter a valid email address." in response.data
    with app.app_context():
        assert Student.query.count() == 0


def test_registration_rejects_short_password(client, app):
    response = client.post(
        "/register",
        data=registration_data(password="short"),
        follow_redirects=True,
    )

    assert b"Password must be at least 8 characters long." in response.data
    with app.app_context():
        assert Student.query.count() == 0


def test_registration_rejects_duplicate_student_id(client, app):
    client.post("/register", data=registration_data())
    response = client.post(
        "/register",
        data=registration_data(email="other@example.com"),
        follow_redirects=True,
    )

    assert b"An account with that student ID or email already exists." in response.data
    with app.app_context():
        assert Student.query.count() == 1


def test_registration_rejects_duplicate_email_case_insensitively(client, app):
    client.post("/register", data=registration_data())
    response = client.post(
        "/register",
        data=registration_data(student_id="S67890", email="STUDENT@example.com"),
        follow_redirects=True,
    )

    assert b"An account with that student ID or email already exists." in response.data
    with app.app_context():
        assert Student.query.count() == 1


def test_registration_stores_password_hash_not_plaintext(client, app):
    password = "securepass"
    client.post("/register", data=registration_data(password=password))

    with app.app_context():
        student = Student.query.one()
        assert student.password_hash != password
        assert check_password_hash(student.password_hash, password)
