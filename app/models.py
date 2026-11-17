from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Student(db.Model):
    """A student account."""

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    gpa = db.Column(db.Float, nullable=False, default=0.0)
    courses = db.relationship("Course", back_populates="student")


class Course(db.Model):
    """A completed course recorded by a student."""

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "course_identifier", name="unique_student_course"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_identifier = db.Column(db.String(80), nullable=False)
    course_name = db.Column(db.String(200), nullable=False)
    credit_hours = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(1), nullable=False)
    student = db.relationship("Student", back_populates="courses")
