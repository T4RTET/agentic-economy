import sqlite3

from fastapi import APIRouter, Depends

from app.database import get_db
from app import repositories
from app.seed import seed_demo_data
from app.schemas import DemoResetResponse


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", response_model=DemoResetResponse)
def reset_demo(db: sqlite3.Connection = Depends(get_db)) -> DemoResetResponse:
    repositories.reset_demo_data(db)
    agents_seeded = seed_demo_data(reset=False, connection=db)
    return {"status": "reset", "agents_seeded": agents_seeded}
