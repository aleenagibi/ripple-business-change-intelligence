from uuid import UUID

from app.api.auth_dependencies import require_organization_access
from app.db.database import get_db
from app.models.user import User
from app.repositories.entity_repository import EntityRepository
from app.schemas.retrieval import (
    HybridRetrievalResult,
    ImpactAnalysisRequest,
    ImpactAnalysisResult,
    RetrievalRequest,
    RetrievalResult,
)
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.retrieval_service import RetrievalService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/organizations/{organization_id}/retrieval",
    tags=["Retrieval"],
)


@router.post(
    "/tfidf",
    response_model=list[RetrievalResult],
)
def tfidf_search(
    organization_id: UUID,
    request: RetrievalRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[RetrievalResult]:
    """Search an organization's documents using TF-IDF."""

    service = RetrievalService(db)

    results = service.search_tfidf(
        organization_id=organization_id,
        query=request.query,
        top_k=request.top_k,
    )

    return [
        RetrievalResult(
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            score=result.score,
            content=result.content,
        )
        for result in results
    ]


@router.post(
    "/dense",
    response_model=list[RetrievalResult],
)
def dense_search(
    organization_id: UUID,
    request: RetrievalRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[RetrievalResult]:
    """Search an organization's documents using dense retrieval."""

    service = RetrievalService(db)

    results = service.search_dense(
        organization_id=organization_id,
        query=request.query,
        top_k=request.top_k,
    )

    return [
        RetrievalResult(
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            score=result.score,
            content=result.content,
        )
        for result in results
    ]


@router.post(
    "/hybrid",
    response_model=list[HybridRetrievalResult],
)
def hybrid_search(
    organization_id: UUID,
    request: RetrievalRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[HybridRetrievalResult]:
    """Search using TF-IDF and dense retrieval with RRF fusion."""

    service = RetrievalService(db)

    results = service.search_hybrid(
        organization_id=organization_id,
        query=request.query,
        top_k=request.top_k,
    )

    return [
        HybridRetrievalResult(
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            score=result.score,
            content=result.content,
            tfidf_rank=result.tfidf_rank,
            dense_rank=result.dense_rank,
        )
        for result in results
    ]


@router.post(
    "/impact-analysis",
    response_model=list[ImpactAnalysisResult],
)
def impact_analysis(
    organization_id: UUID,
    request: ImpactAnalysisRequest,
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> list[ImpactAnalysisResult]:
    """
    Analyze the potential business impact of a requirement change.
    """

    service = ImpactAnalysisService(db)
    entity_repository = EntityRepository(db)

    results = service.analyze(
        organization_id=organization_id,
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
            path=[str(entity_id) for entity_id in result.path],
            explanation=result.explanation,
            source_documents=[
                {
                    "document_id": str(document_id),
                    "filename": filename,
                }
                for document_id, filename in (
                    entity_repository
                    .list_source_documents_for_canonical_entity(
                        result.entity_id
                    )
                )
            ],
        )
        for result in results
    ]
