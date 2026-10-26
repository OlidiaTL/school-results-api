import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(enum.StrEnum):
    admin = "admin"  # manages users, students and subjects
    teacher = "teacher"  # records and reads results


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.teacher)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("form BETWEEN 1 AND 6", name="ck_students_form_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    form: Mapped[int] = mapped_column(Integer, index=True)
    house: Mapped[str | None] = mapped_column(String(60))

    results: Mapped[list["Result"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class Result(Base):
    """One assessment score for one student, in one subject, in one term."""

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "term", name="uq_results_student_subject_term"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_results_score_range"),
        # Supports the at-risk query, which groups every student's scores by term.
        Index("ix_results_student_term", "student_id", "term"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    term: Mapped[str] = mapped_column(String(7))  # e.g. "2026-T2"; sorts chronologically as text
    score: Mapped[float] = mapped_column(Float)
    assessed_on: Mapped[date] = mapped_column(Date)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    student: Mapped[Student] = relationship(back_populates="results")
    subject: Mapped[Subject] = relationship()
