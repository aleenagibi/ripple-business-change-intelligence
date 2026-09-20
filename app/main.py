from app.api.auth_routes import router as auth_router
from app.api.document_routes import router as document_router
from app.api.organization_routes import router as organization_router
from app.api.retrieval_routes import router as retrieval_router
from app.core.config import settings
from app.db.database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    organization_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    document_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    retrieval_router,
    prefix=settings.API_PREFIX,
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }