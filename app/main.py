from fastapi import FastAPI
from sqlalchemy import text

from app.config import get_settings
from app.deps import DbSession
from app.routers import auth, results, students, subjects

app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="Record secondary-school assessment results and flag students who need early support.",
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(subjects.router)
app.include_router(results.router)


@app.get("/health", tags=["health"])
def health(db: DbSession):
    """Liveness check that also confirms the database is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
