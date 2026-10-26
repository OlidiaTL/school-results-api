from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import AdminUser, DbSession, StaffUser
from app.models import Subject
from app.schemas import SubjectCreate, SubjectOut

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectOut])
def list_subjects(db: DbSession, _: StaffUser):
    return db.scalars(select(Subject).order_by(Subject.code)).all()


@router.post("", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: DbSession, _: AdminUser):
    code = payload.code.upper()
    if db.scalar(select(Subject).where(Subject.code == code)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subject code already exists")
    subject = Subject(code=code, name=payload.name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
