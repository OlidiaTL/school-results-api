from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession, StaffUser
from app.models import Result, Student, Subject
from app.schemas import TERM_PATTERN, AtRiskStudent, ResultCreate, ResultOut
from app.services.analytics import at_risk_students

router = APIRouter(prefix="/results", tags=["results"])


@router.post("", response_model=ResultOut, status_code=status.HTTP_201_CREATED)
def record_result(payload: ResultCreate, db: DbSession, user: StaffUser):
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    result = Result(**payload.model_dump(), recorded_by_id=user.id)
    db.add(result)
    try:
        db.commit()
    except IntegrityError as exc:
        # The unique constraint on (student, subject, term) is the source of truth,
        # which also protects against two teachers submitting at the same moment.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A result for this student, subject and term already exists",
        ) from exc
    db.refresh(result)
    return result


@router.get("", response_model=list[ResultOut])
def list_results(
    db: DbSession,
    _: StaffUser,
    student_id: int | None = None,
    subject_id: int | None = None,
    term: str | None = Query(default=None, pattern=TERM_PATTERN),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = select(Result)
    if student_id is not None:
        query = query.where(Result.student_id == student_id)
    if subject_id is not None:
        query = query.where(Result.subject_id == subject_id)
    if term is not None:
        query = query.where(Result.term == term)
    query = query.order_by(Result.term.desc(), Result.id).limit(limit).offset(offset)
    return db.scalars(query).all()


@router.get("/at-risk", response_model=list[AtRiskStudent])
def list_at_risk(db: DbSession, _: StaffUser, form: int | None = Query(default=None, ge=1, le=6)):
    """Students whose latest term average is below the threshold or has dropped sharply."""
    return at_risk_students(db, form=form)
