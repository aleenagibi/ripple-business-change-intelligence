"""
Hugging Face ZeroGPU deployment adapter for Ripple.
This module is deployment-specific.
Ripple's existing application architecture remains unchanged:
    React
        ↓
    FastAPI
        ↓
    Ripple Services
        ↓
    Hybrid Retrieval
        ↓
    Knowledge Graph
        ↓
    Impact Analysis
The adapter provides the Hugging Face ZeroGPU runtime while preserving
Ripple's existing REST API contract.
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import Generator
from uuid import UUID

# IMPORTANT:
# spaces must be imported before torch/sentence-transformers so that
# ZeroGPU can install its CUDA interception layer.
import spaces
from fastapi import Depends, File, HTTPException, UploadFile
from gradio import Server
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.api.auth_dependencies import require_organization_access
from app.api.auth_routes import router as auth_router
from app.api.organization_routes import router as organization_router
from app.api.retrieval_routes import router as retrieval_router
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.schemas.retrieval import (
    ImpactAnalysisRequest,
    ImpactAnalysisResult,
)
from app.services.document_service import DocumentService
from app.services.impact_analysis_service import ImpactAnalysisService

# ---------------------------------------------------------------------------
# Gradio Server
# ---------------------------------------------------------------------------

server = Server(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
#
# Ripple already defines its CORS policy in app.main.
# Recreate the same policy here so the React frontend can communicate
# with the Hugging Face backend.
#

from fastapi.middleware.cors import CORSMiddleware

server.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Database helper for ZeroGPU worker
# ---------------------------------------------------------------------------

def _open_database_session() -> Generator[Session, None, None]:
    """
    Open a database session for the ZeroGPU worker.
    A separate session is created inside the GPU execution boundary.
    SQLAlchemy Session objects should not be passed into a ZeroGPU worker
    as function arguments.
    """

    database_generator = get_db()

    db = next(database_generator)

    try:
        yield db
    finally:
        database_generator.close()


# ---------------------------------------------------------------------------
# GPU execution boundary
# ---------------------------------------------------------------------------

@spaces.GPU(duration=120)
def _run_impact_analysis_on_gpu(
    organization_id: str,
    query: str,
    top_k: int,
    max_distance: int,
) -> list:
    """
    Execute Ripple's complete impact-analysis pipeline inside ZeroGPU.
    The function accepts only primitive serializable values. It creates
    its own database session inside the ZeroGPU execution boundary.
    This allows the existing Ripple services to remain unchanged while
    Sentence Transformer inference performed by:
        DenseRetrievalEngine
        ImpactAnalysisService
    executes while the ZeroGPU allocation is active.
    """

    organization_uuid = UUID(organization_id)

    database_generator = get_db()
    db = next(database_generator)

    try:
        service = ImpactAnalysisService(db)

        return service.analyze(
            organization_id=organization_uuid,
            query=query,
            top_k=top_k,
            max_distance=max_distance,
        )

    finally:
        database_generator.close()

@spaces.GPU(duration=120)
async def _upload_document_on_gpu(
    organization_id: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> DocumentResponse:
    """
    Execute document ingestion inside the ZeroGPU boundary.

    The entire DocumentService lifecycle is created inside the GPU
    execution context because entity canonical resolution may initialize
    a SentenceTransformer model.
    """

    organization_uuid = UUID(organization_id)

    database_generator = get_db()
    db = next(database_generator)

    upload = UploadFile(
        filename=filename,
        file=BytesIO(file_bytes),
        headers=Headers(
            {
                "content-type": content_type,
            }
        ),
    )

    try:
        service = DocumentService(db)

        document = await service.upload(
            organization_id=organization_uuid,
            upload=upload,
        )

        return DocumentResponse.model_validate(document)

    finally:
        database_generator.close()

@server.post(
    f"{settings.API_PREFIX}"
    "/organizations/{organization_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
    tags=["Documents"],
)
async def upload_document(
    organization_id: UUID,
    file: UploadFile = File(...),
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Upload and process a business document through the ZeroGPU
    execution boundary.

    Authentication is performed outside the GPU worker.
    Document processing, including semantic entity resolution,
    occurs inside the GPU worker.
    """

    del db

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        return await _upload_document_on_gpu(
            organization_id=str(organization_id),
            filename=file.filename or "",
            content_type=file.content_type
            or "application/octet-stream",
            file_bytes=file_bytes,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Organization not found.":
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=400,
            detail=message,
        ) from exc
# ---------------------------------------------------------------------------
# Existing authentication / organization / document routes
# ---------------------------------------------------------------------------

server.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
)

server.include_router(
    organization_router,
    prefix=settings.API_PREFIX,
)




# ---------------------------------------------------------------------------
# Existing retrieval routes except impact-analysis
# ---------------------------------------------------------------------------
#
# The existing retrieval router contains:
#
#   /tfidf
#   /dense
#   /hybrid
#   /impact-analysis
#
# We register the normal retrieval router after our deployment-specific
# impact-analysis route below. FastAPI uses route order, so the
# deployment-specific route handles /impact-analysis while the existing
# router continues to handle TF-IDF, dense, and hybrid retrieval.
#

# ---------------------------------------------------------------------------
# ZeroGPU-compatible impact-analysis endpoint
# ---------------------------------------------------------------------------

@server.post(
    f"{settings.API_PREFIX}"
    "/organizations/{organization_id}/retrieval/impact-analysis",
    response_model=list[ImpactAnalysisResult],
    tags=["Retrieval"],
)
def impact_analysis(
    organization_id: UUID,
    request: ImpactAnalysisRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[ImpactAnalysisResult]:
    """
    Analyze the potential business impact of a requirement change.
    Authentication and organization access are validated by the normal
    FastAPI dependency system.
    The actual NLP-heavy impact-analysis pipeline is then executed
    through the ZeroGPU boundary.
    """

    # The dependency session is intentionally used for authentication
    # only. The GPU worker creates its own independent database session.
    del db

    results = _run_impact_analysis_on_gpu(
        organization_id=str(organization_id),
        query=request.query,
        top_k=request.top_k,
        max_distance=request.max_distance,
    )

    return [
        ImpactAnalysisResult(
            entity_id=str(result.entity_id),
            name=result.name,
            entity_type=result.entity_type,
            impact_score=result.impact_score,
            impact_level=result.impact_level,
            impact_origin=result.impact_origin,
            impact_category=result.impact_category,
            semantic_relevance=result.semantic_relevance,
            relationship_strength=result.relationship_strength,
            graph_proximity=result.graph_proximity,
            entity_importance=result.entity_importance,
            propagation_distance=result.propagation_distance,
            path=[
                str(entity_id)
                for entity_id in result.path
            ],
            explanation=result.explanation,
        )
        for result in results
    ]


# ---------------------------------------------------------------------------
# Remaining retrieval routes
# ---------------------------------------------------------------------------

server.include_router(
    retrieval_router,
    prefix=settings.API_PREFIX,
)


# ---------------------------------------------------------------------------
# Root and health endpoints
# ---------------------------------------------------------------------------

@server.get(
    "/",
    tags=["Root"],
)
async def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@server.get(
    "/hf-health",
    tags=["Health"],
)
async def hf_health() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "deployment": "huggingface-zerogpu",
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server.launch(
        server_name="0.0.0.0",
        server_port=int(
            os.getenv("PORT", "7860")
        ),
        show_error=True,
    )