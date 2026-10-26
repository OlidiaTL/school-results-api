"""Analytics queries.

Both functions push the heavy lifting (grouping and averaging) into the database in a
single query, instead of loading every result row into Python or querying once per
student (the classic N+1 problem).
"""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Result, Student, Subject
from app.schemas import AtRiskStudent, StudentOut, StudentSummary, SubjectAverage


def student_summary(db: Session, student: Student) -> StudentSummary:
    rows = db.execute(
        select(
            Subject.code,
            Subject.name,
            func.avg(Result.score).label("average_score"),
            func.count(Result.id).label("assessments"),
        )
        .join(Subject, Subject.id == Result.subject_id)
        .where(Result.student_id == student.id)
        .group_by(Subject.code, Subject.name)
        .order_by(Subject.code)
    ).all()

    subjects = [
        SubjectAverage(
            subject_code=r.code,
            subject_name=r.name,
            average_score=round(r.average_score, 1),
            assessments=r.assessments,
        )
        for r in rows
    ]
    overall = db.scalar(select(func.avg(Result.score)).where(Result.student_id == student.id))
    return StudentSummary(
        student=StudentOut.model_validate(student),
        overall_average=round(overall, 1) if overall is not None else None,
        subjects=subjects,
    )


def at_risk_students(db: Session, form: int | None = None) -> list[AtRiskStudent]:
    """Flag students whose latest term average is low, or has dropped sharply.

    Step 1 (SQL): average each student's scores per term.
    Step 2 (SQL): rank each student's terms newest-first with ROW_NUMBER() and keep the top two.
    Step 3 (Python): compare the latest term with the previous one and apply the thresholds.
    """
    settings = get_settings()

    term_averages = (
        select(
            Result.student_id,
            Result.term,
            func.avg(Result.score).label("avg_score"),
        )
        .group_by(Result.student_id, Result.term)
        .subquery()
    )

    ranked = select(
        term_averages,
        func.row_number()
        .over(partition_by=term_averages.c.student_id, order_by=term_averages.c.term.desc())
        .label("term_rank"),
    ).subquery()

    query = (
        select(Student, ranked.c.term, ranked.c.avg_score, ranked.c.term_rank)
        .join(ranked, ranked.c.student_id == Student.id)
        .where(ranked.c.term_rank <= 2)
        .order_by(Student.id, ranked.c.term_rank)
    )
    if form is not None:
        query = query.where(Student.form == form)

    students: dict[int, Student] = {}
    terms_by_student: dict[int, list[tuple[str, float]]] = defaultdict(list)  # newest term first
    for student, term, avg_score, _rank in db.execute(query):
        students[student.id] = student
        terms_by_student[student.id].append((term, float(avg_score)))

    flagged: list[AtRiskStudent] = []
    for student_id, terms in terms_by_student.items():
        student = students[student_id]
        latest_term, latest_avg = terms[0]
        previous_avg = terms[1][1] if len(terms) > 1 else None
        change = round(latest_avg - previous_avg, 1) if previous_avg is not None else None

        reasons = []
        if latest_avg < settings.at_risk_score_threshold:
            reasons.append(f"Latest term average below {settings.at_risk_score_threshold:g}%")
        if change is not None and change <= -settings.at_risk_drop_threshold:
            reasons.append(f"Average dropped {abs(change):g} points since previous term")

        if reasons:
            flagged.append(
                AtRiskStudent(
                    student_id=student.id,
                    student_number=student.student_number,
                    full_name=f"{student.first_name} {student.last_name}",
                    form=student.form,
                    latest_term=latest_term,
                    latest_average=round(latest_avg, 1),
                    previous_average=round(previous_avg, 1) if previous_avg is not None else None,
                    change=change,
                    reasons=reasons,
                )
            )

    # Most urgent first: lowest latest average.
    return sorted(flagged, key=lambda s: s.latest_average)
