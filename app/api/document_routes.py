from uuid import UUID

from app.api.auth_dependencies import require_organization_access
from app.db.database import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/organizations/{organization_id}/documents",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    organization_id: UUID,
    file: UploadFile = File(...),
    _: User = Depends(require_organization_access),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = DocumentService(db)

    try:
        document = await service.upload(
            organization_id=organization_id,
            upload=file,
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

    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=list[DocumentResponse],
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


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
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