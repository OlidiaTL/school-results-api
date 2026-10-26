"""Load demo data: two staff accounts, five subjects, 12 fictional students and three terms of results.

Usage (after `alembic upgrade head`):
    python -m scripts.seed
"""

import random
from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Result, Role, Student, Subject, User
from app.security import hash_password

SUBJECTS = [
    ("CS", "Computer Science"),
    ("MATH", "Mathematics"),
    ("ACC", "Accounting"),
    ("ENG", "English Language"),
    ("BIO", "Biology"),
]
FIRST_NAMES = [
    "Tariro",
    "Kuda",
    "Rudo",
    "Tendai",
    "Nyasha",
    "Farai",
    "Chipo",
    "Tafadzwa",
    "Anesu",
    "Ruvimbo",
    "Simba",
    "Thandeka",
]
LAST_NAMES = [
    "Moyo",
    "Ncube",
    "Dube",
    "Sibanda",
    "Ndlovu",
    "Mpofu",
    "Chikomo",
    "Nyathi",
    "Mlilo",
    "Khumalo",
    "Banda",
    "Phiri",
]
HOUSES = ["Baobab", "Kudu", "Msasa", "Zambezi"]
TERMS = [("2026-T1", date(2026, 4, 2)), ("2026-T2", date(2026, 8, 6)), ("2026-T3", date(2026, 11, 26))]


def main() -> None:
    rng = random.Random(42)  # fixed seed: the same demo data every run
    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)):
            print("Database already has data; skipping seed.")
            return

        admin = User(
            email="admin@example.com",
            full_name="Demo Admin",
            role=Role.admin,
            hashed_password=hash_password("admin12345"),
        )
        teacher = User(
            email="teacher@example.com",
            full_name="Demo Teacher",
            role=Role.teacher,
            hashed_password=hash_password("teacher12345"),
        )
        subjects = [Subject(code=c, name=n) for c, n in SUBJECTS]
        db.add_all([admin, teacher, *subjects])
        db.flush()

        for i, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES, strict=True), start=1):
            student = Student(
                student_number=f"STU{2026000 + i}",
                first_name=first,
                last_name=last,
                form=3 + i % 3,
                house=HOUSES[i % len(HOUSES)],
            )
            db.add(student)
            db.flush()

            base = rng.uniform(45, 85)
            # A few students decline sharply over the year, so /results/at-risk has something to show.
            trend = -9 if i % 4 == 0 else rng.uniform(-2, 3)
            for t, (term, assessed_on) in enumerate(TERMS):
                for subject in subjects:
                    score = base + trend * t + rng.uniform(-6, 6)
                    db.add(
                        Result(
                            student_id=student.id,
                            subject_id=subject.id,
                            term=term,
                            score=round(min(max(score, 0), 100), 1),
                            assessed_on=assessed_on,
                            recorded_by_id=teacher.id,
                        )
                    )
        db.commit()
        print("Seeded 2 users, 5 subjects, 12 students and 180 results.")
        print("Log in as admin@example.com / admin12345 or teacher@example.com / teacher12345")
    finally:
        db.close()


if __name__ == "__main__":
    main()
