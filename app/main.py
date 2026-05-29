from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers.agents import router as agents_router
from app.routers.automation import router as automation_router
from app.routers.auth import router as auth_router
from app.routers.demo import router as demo_router
from app.routers.intelligence import router as intelligence_router
from app.routers.marketplace import router as marketplace_router
from app.routers.project import router as project_router
from app.routers.wallet import router as wallet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Agent Reputation Passport API",
    description="Backend MVP for AI-agent trust, risk, and wallet-limit reputation passports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(agents_router)
app.include_router(auth_router)
app.include_router(wallet_router)
app.include_router(demo_router)
app.include_router(marketplace_router)
app.include_router(intelligence_router)
app.include_router(automation_router)
app.include_router(project_router)
