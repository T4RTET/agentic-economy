from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import connect, init_db
from app.middleware import RateLimitMiddleware
from app.routers.agents import router as agents_router
from app.routers.automation import router as automation_router
from app.routers.auth import router as auth_router
from app.routers.demo import router as demo_router
from app.routers.intelligence import router as intelligence_router
from app.routers.marketplace import router as marketplace_router
from app.routers.mantle import router as mantle_router
from app.routers.project import router as project_router
from app.routers.wallet import router as wallet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.seed import seed_demo_data

    seed_demo_data()
    yield


app = FastAPI(
    title="Agent Reputation Passport API",
    description="Backend MVP for AI-agent trust, risk, and wallet-limit reputation passports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    connection = connect()
    try:
        connection.execute("SELECT 1").fetchone()
        return {"status": "ready", "database": "connected"}
    finally:
        connection.close()


app.include_router(agents_router)
app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(demo_router)
app.include_router(marketplace_router)
app.include_router(intelligence_router)
app.include_router(automation_router)
app.include_router(project_router)
app.include_router(mantle_router)
