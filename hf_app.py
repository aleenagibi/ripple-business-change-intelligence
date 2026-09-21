from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Generator
from uuid import UUID

import spaces
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
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


server = Server(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)


server.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://ripple-business-change-intelligence.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _open_database_session() -> Generator[Session, None, None]:
    database_generator = get_db()
    db = next(database_generator)

    try:
        yield db
    finally:
        database_generator.close()


@spaces.GPU(duration=120)
def _run_impact_analysis_on_gpu(
    organization_id: str,
    query: str,
    top_k: int,
    max_distance: int,
) -> list:
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
def _upload_document_on_gpu(
    organization_id: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> DocumentResponse:
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

        document = asyncio.run(
            service.upload(
                organization_id=organization_uuid,
                upload=upload,
            )
        )

        return DocumentResponse.model_validate(document)

    finally:
        database_generator.close()


# ---------------------------------------------------------------------------
# Authentication
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
# Document upload
#
# POST is deployment-specific because document processing initializes
# NLP / embedding models and therefore must execute inside ZeroGPU.
# ---------------------------------------------------------------------------

@server.post(
    f"{settings.API_PREFIX}/organizations/{{organization_id}}/documents",
    response_model=DocumentResponse,
    status_code=201,
    tags=["Documents"],
)
def upload_document(
    organization_id: UUID,
    file: UploadFile = File(...),
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    del db

    try:
        file_bytes = file.file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        if len(file_bytes) > DocumentService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File exceeds the maximum allowed size of 25 MB.",
            )

        return _upload_document_on_gpu(
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

    finally:
        file.file.close()


# ---------------------------------------------------------------------------
# Document listing
#
# GET does not perform NLP processing. It only reads persisted documents
# from PostgreSQL.
# ---------------------------------------------------------------------------

@server.get(
    f"{settings.API_PREFIX}/organizations/{{organization_id}}/documents",
    response_model=list[DocumentResponse],
    tags=["Documents"],
)
def list_documents(
    organization_id: UUID,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    service = DocumentService(db)

    documents = service.document_repository.list_by_organization(
        organization_id,
    )

    return [
        DocumentResponse.model_validate(document)
        for document in documents
    ]


# ---------------------------------------------------------------------------
# Single document
# ---------------------------------------------------------------------------

@server.get(
    f"{settings.API_PREFIX}/organizations/{{organization_id}}/documents/{{document_id}}",
    response_model=DocumentResponse,
    tags=["Documents"],
)
def get_document(
    organization_id: UUID,
    document_id: UUID,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = DocumentService(db)

    document = service.document_repository.get_by_id(
        document_id=document_id,
        organization_id=organization_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return DocumentResponse.model_validate(document)


# ---------------------------------------------------------------------------
# Impact analysis
#
# The analysis itself uses embedding models and therefore executes inside
# ZeroGPU.
# ---------------------------------------------------------------------------

@server.post(
    f"{settings.API_PREFIX}/organizations/{{organization_id}}/retrieval/impact-analysis",
    response_model=list[ImpactAnalysisResult],
    tags=["Retrieval"],
)
def impact_analysis(
    organization_id: UUID,
    request: ImpactAnalysisRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[ImpactAnalysisResult]:
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
# Existing retrieval routes
# ---------------------------------------------------------------------------

server.include_router(
    retrieval_router,
    prefix=settings.API_PREFIX,
)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@server.get("/")
async def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


# ---------------------------------------------------------------------------
# Hugging Face health check
# ---------------------------------------------------------------------------

@server.get("/hf-health")
async def hf_health() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "deployment": "huggingface-zerogpu",
    }


if __name__ == "__main__":
    server.launch(
        server_name="0.0.0.0",
        server_port=7860,
    )