import re

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import Course, Student, db


main = Blueprint("main", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GRADE_POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}


def get_authenticated_student():
    """Return the logged-in student, clearing a stale session if necessary."""
    student_id = session.get("student_id")
    student = db.session.get(Student, student_id) if student_id is not None else None
    if student is None:
        session.pop("student_id", None)
    return student


def update_gpa(student):
    """Recalculate a student's credit-hour-weighted GPA."""
    total_hours = sum(course.credit_hours for course in student.courses)
    if not total_hours:
        student.gpa = 0.0
        return
    quality_points = sum(
        GRADE_POINTS[course.grade] * course.credit_hours
        for course in student.courses
    )
    student.gpa = round(quality_points / total_hours, 2)


@main.route("/")
def index():
    """Show the login page."""
    return redirect(url_for("main.login"))


@main.route("/register", methods=["GET", "POST"])
def register():
    """Register a student account."""
    if request.method == "GET":
        return render_template("register.html")

    student_id = request.form.get("student_id", "").strip()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not student_id or not full_name or not email or not password:
        flash("All fields are required.", "error")
        return render_template("register.html")
    if not EMAIL_PATTERN.fullmatch(email):
        flash("Enter a valid email address.", "error")
        return render_template("register.html")
    if len(password) < 8:
        flash("Password must be at least 8 characters long.", "error")
        return render_template("register.html")

    existing_student = Student.query.filter(
        or_(Student.student_id == student_id, Student.email == email)
    ).first()
    if existing_student:
        flash("An account with that student ID or email already exists.", "error")
        return render_template("register.html")

    student = Student(
        student_id=student_id,
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(student)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("An account with that student ID or email already exists.", "error")
        return render_template("register.html")

    flash("Registration successful. Please log in.", "success")
    return redirect(url_for("main.login"))


@main.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a student using their student ID or email."""
    if request.method == "GET":
        return render_template("login.html")

    identifier = request.form.get("identifier", "").strip()
    password = request.form.get("password", "")
    student = Student.query.filter(
        or_(Student.student_id == identifier, Student.email == identifier.lower())
    ).first()
    if not identifier or not password or not student or not check_password_hash(
        student.password_hash, password
    ):
        flash("Invalid student ID/email or password.", "error")
        return render_template("login.html")

    session["student_id"] = student.id
    flash("You are logged in.", "success")
    return redirect(url_for("main.dashboard"))


@main.route("/dashboard")
def dashboard():
    """Show the protected student dashboard."""
    student = get_authenticated_student()
    if student is None:
        flash("Please log in to access that page.", "warning")
        return redirect(url_for("main.login"))

    return render_template(
        "dashboard.html",
        student=student,
        courses=Course.query.filter_by(student_id=student.id).order_by(
            Course.course_identifier
        ).all(),
    )


@main.route("/courses/add", methods=["POST"])
def add_course():
    """Record a completed course and update the student's GPA."""
    student = get_authenticated_student()
    if student is None:
        flash("Please log in to access that page.", "warning")
        return redirect(url_for("main.login"))

    course_identifier = request.form.get("course_identifier", "").strip()
    course_name = request.form.get("course_name", "").strip()
    credit_hours_value = request.form.get("credit_hours", "").strip()
    grade = request.form.get("grade", "").strip().upper()
    if not course_identifier or not course_name or not credit_hours_value or not grade:
        flash("All course fields are required.", "error")
        return redirect(url_for("main.dashboard"))

    if (
        not re.fullmatch(r"[0-9]+", credit_hours_value)
        or int(credit_hours_value) < 1
    ):
        flash("Credit hours must be a positive whole number.", "error")
        return redirect(url_for("main.dashboard"))
    if grade not in GRADE_POINTS:
        flash("Letter grade must be A, B, C, D, or F.", "error")
        return redirect(url_for("main.dashboard"))

    existing_course = Course.query.filter_by(
        student_id=student.id,
        course_identifier=course_identifier,
    ).first()
    if existing_course:
        flash("You have already recorded that course identifier.", "error")
        return redirect(url_for("main.dashboard"))

    course = Course(
        student_id=student.id,
        course_identifier=course_identifier,
        course_name=course_name,
        credit_hours=int(credit_hours_value),
        grade=grade,
    )
    db.session.add(course)
    update_gpa(student)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("You have already recorded that course identifier.", "error")
        return redirect(url_for("main.dashboard"))

    flash("Completed course added successfully.", "success")
    return redirect(url_for("main.dashboard"))


@main.route("/logout", methods=["POST"])
def logout():
    """End the student's authenticated session."""
    session.pop("student_id", None)
    flash("You are logged out.", "success")
    return redirect(url_for("main.login"))
