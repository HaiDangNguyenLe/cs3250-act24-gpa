import pytest

from app.models import Course, Student


def register_and_log_in(client, **student_data):
    """Create and authenticate a student for course tests."""
    data = {
        "student_id": "S12345",
        "full_name": "A Student",
        "email": "student@example.com",
        "password": "securepass",
    }
    data.update(student_data)
    client.post("/register", data=data)
    return client.post(
        "/login",
        data={"identifier": data["student_id"], "password": data["password"]},
    )


def course_data(**updates):
    """Return valid course form data with any requested changes."""
    data = {
        "course_identifier": "CS101",
        "course_name": "Introduction to Computing",
        "credit_hours": "3",
        "grade": "A",
    }
    data.update(updates)
    return data


def test_add_course_displays_course_and_updates_student_gpa(client, app):
    register_and_log_in(client)

    response = client.post(
        "/courses/add",
        data=course_data(),
        follow_redirects=True,
    )

    assert b"Completed course added successfully." in response.data
    assert b"CS101" in response.data
    assert b"Introduction to Computing" in response.data
    assert b">3<" in response.data
    assert b">A<" in response.data
    assert b"GPA: 4.00" in response.data
    with app.app_context():
        assert Course.query.count() == 1
        student = Student.query.one()
        assert student.gpa == 4.0


@pytest.mark.parametrize(
    "field",
    ["course_identifier", "course_name", "credit_hours", "grade"],
)
def test_add_course_rejects_missing_required_field(client, app, field):
    register_and_log_in(client)

    response = client.post(
        "/courses/add",
        data=course_data(**{field: ""}),
        follow_redirects=True,
    )

    assert b"All course fields are required." in response.data
    with app.app_context():
        assert Course.query.count() == 0
        assert Student.query.one().gpa == 0.0


@pytest.mark.parametrize("credit_hours", ["0", "-1", "1.5", "abc"])
def test_add_course_rejects_invalid_credit_hours(client, app, credit_hours):
    register_and_log_in(client)

    response = client.post(
        "/courses/add",
        data=course_data(credit_hours=credit_hours),
        follow_redirects=True,
    )

    assert b"Credit hours must be a positive whole number." in response.data
    with app.app_context():
        assert Course.query.count() == 0
        assert Student.query.one().gpa == 0.0


@pytest.mark.parametrize("grade", ["E", "A+", ""])
def test_add_course_rejects_invalid_letter_grade(client, app, grade):
    register_and_log_in(client)
    data = course_data(grade=grade)
    if not grade:
        data["grade"] = " "

    response = client.post(
        "/courses/add",
        data=data,
        follow_redirects=True,
    )

    expected_message = (
        b"All course fields are required."
        if not grade
        else b"Letter grade must be A, B, C, D, or F."
    )
    assert expected_message in response.data
    with app.app_context():
        assert Course.query.count() == 0


def test_add_course_rejects_duplicate_identifier_for_same_student(client, app):
    register_and_log_in(client)
    client.post("/courses/add", data=course_data())

    response = client.post(
        "/courses/add",
        data=course_data(course_name="Different name"),
        follow_redirects=True,
    )

    assert b"You have already recorded that course identifier." in response.data
    with app.app_context():
        assert Course.query.count() == 1
        student = Student.query.one()
        assert student.gpa == 4.0


def test_add_course_recalculates_weighted_gpa(client, app):
    register_and_log_in(client)
    client.post("/courses/add", data=course_data(grade="A", credit_hours="3"))

    response = client.post(
        "/courses/add",
        data=course_data(
            course_identifier="CS102",
            course_name="Programming",
            credit_hours="1",
            grade="B",
        ),
        follow_redirects=True,
    )

    assert b"GPA: 3.75" in response.data
    with app.app_context():
        assert Student.query.one().gpa == 3.75


def test_unauthenticated_student_cannot_add_course(client, app):
    response = client.post(
        "/courses/add",
        data=course_data(),
        follow_redirects=True,
    )

    assert b"Please log in to access that page." in response.data
    with app.app_context():
        assert Course.query.count() == 0
