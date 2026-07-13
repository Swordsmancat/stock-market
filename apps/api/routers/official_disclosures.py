from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.providers.cninfo_disclosure_provider import CninfoDisclosureProviderError
from packages.providers.cninfo_document_provider import CninfoDocumentProviderError
from packages.services.official_disclosure_documents import (
    OfficialDisclosureDocumentNotFoundError,
    OfficialDisclosureDocumentPersistenceError,
    OfficialDisclosureDocumentStorageError,
    ingest_official_disclosure_document,
    list_official_disclosure_sections,
)
from packages.services.official_disclosures import (
    OfficialDisclosurePersistenceError,
    OfficialDisclosureRefreshInput,
    list_official_disclosures,
    refresh_official_disclosures,
)
from packages.shared.database import get_session


router = APIRouter(prefix="/official-disclosures", tags=["official-disclosures"])


class OfficialDisclosureRefreshRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    start_date: date
    end_date: date
    category: str | None = Field(default=None, max_length=128)


@router.get("")
def list_disclosures(
    symbol: str = Query(min_length=1, max_length=16),
    limit: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return list_official_disclosures(session=session, symbol=symbol, limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/refresh")
def refresh_disclosures(
    payload: OfficialDisclosureRefreshRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return refresh_official_disclosures(
            OfficialDisclosureRefreshInput(
                symbol=payload.symbol,
                start_date=payload.start_date,
                end_date=payload.end_date,
                category=payload.category,
            ),
            session=session,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except CninfoDisclosureProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={"source": "cninfo", "code": error.code, "message": error.message},
        ) from error
    except OfficialDisclosurePersistenceError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/{disclosure_id}/ingest-document")
def ingest_disclosure_document(
    disclosure_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return ingest_official_disclosure_document(disclosure_id, session=session)
    except OfficialDisclosureDocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except CninfoDocumentProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={"source": "cninfo", "code": error.code, "message": error.message},
        ) from error
    except (OfficialDisclosureDocumentPersistenceError, OfficialDisclosureDocumentStorageError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/{disclosure_id}/sections")
def list_disclosure_sections(
    disclosure_id: str,
    document_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return list_official_disclosure_sections(
            disclosure_id,
            session=session,
            document_id=document_id,
            limit=limit,
        )
    except OfficialDisclosureDocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
