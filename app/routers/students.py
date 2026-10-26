from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import AdminUser, DbSession, StaffUser
from app.models import Student
from app.schemas import StudentCreate, StudentOut, StudentPage, StudentSummary, StudentUpdate
from app.services.analytics import student_summary

router = APIRouter(prefix="/students", tags=["students"])


def _get_student_or_404(db: DbSession, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.get("", response_model=StudentPage)
def list_students(
    db: DbSession,
    _: StaffUser,
    form: int | None = Query(default=None, ge=1, le=6),
    search: str | None = Query(default=None, min_length=1, description="Match on first or last name"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Student)
    if form is not None:
        query = query.where(Student.form == form)
    if search:
        pattern = f"%{search}%"
        query = query.where(Student.first_name.ilike(pattern) | Student.last_name.ilike(pattern))

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Student.last_name, Student.first_name).limit(limit).offset(offset)).all()
    return StudentPage(total=total, limit=limit, offset=offset, items=items)


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: DbSession, _: AdminUser):
    if db.scalar(select(Student).where(Student.student_number == payload.student_number)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student number already exists")
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: DbSession, _: StaffUser):
    return _get_student_or_404(db, student_id)


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: DbSession, _: AdminUser):
    student = _get_student_or_404(db, student_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: DbSession, _: AdminUser):
    db.delete(_get_student_or_404(db, student_id))
    db.commit()


@router.get("/{student_id}/summary", response_model=StudentSummary)
def get_student_summary(student_id: int, db: DbSession, _: StaffUser):
    """Per-subject averages and an overall average for one student."""
    return student_summary(db, _get_student_or_404(db, student_id))
