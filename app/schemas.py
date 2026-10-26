from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role

TERM_PATTERN = r"^\d{4}-T[1-3]$"  # e.g. 2026-T1


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8)
    role: Role = Role.teacher


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role


# ---------- students ----------
class StudentBase(BaseModel):
    student_number: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    form: int = Field(ge=1, le=6)
    house: str | None = Field(default=None, max_length=60)


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    form: int | None = Field(default=None, ge=1, le=6)
    house: str | None = Field(default=None, max_length=60)


class StudentOut(ORMModel, StudentBase):
    id: int


class StudentPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[StudentOut]


# ---------- subjects ----------
class SubjectCreate(BaseModel):
    code: str = Field(min_length=2, max_length=10)
    name: str = Field(min_length=1, max_length=100)


class SubjectOut(ORMModel, SubjectCreate):
    id: int


# ---------- results ----------
class ResultCreate(BaseModel):
    student_id: int
    subject_id: int
    term: str = Field(pattern=TERM_PATTERN, examples=["2026-T2"])
    score: float = Field(ge=0, le=100)
    assessed_on: date


class ResultOut(ORMModel):
    id: int
    student_id: int
    subject_id: int
    term: str
    score: float
    assessed_on: date
    recorded_by_id: int | None


# ---------- analytics ----------
class SubjectAverage(BaseModel):
    subject_code: str
    subject_name: str
    average_score: float
    assessments: int


class StudentSummary(BaseModel):
    student: StudentOut
    overall_average: float | None
    subjects: list[SubjectAverage]


class AtRiskStudent(BaseModel):
    student_id: int
    student_number: str
    full_name: str
    form: int
    latest_term: str
    latest_average: float
    previous_average: float | None
    change: float | None
    reasons: list[str]
