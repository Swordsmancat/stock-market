from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from packages.services.source_ingestion import (
    SourceIngestionExtractionInput,
    extract_source_ingestion_payload,
)


router = APIRouter(prefix="/source-ingestion", tags=["source-ingestion"])


class SourceIngestionExtractRequest(BaseModel):
    content: str = Field(default="", max_length=12000)
    filename: str | None = Field(default=None, max_length=256)
    source_url: str | None = Field(default=None, max_length=1024)
    source_id: str | None = Field(default=None, max_length=128)
    source_label: str | None = Field(default=None, max_length=256)
    source_category: str | None = Field(default=None, max_length=64)
    target_indicator_codes: list[str] = Field(default_factory=list)
    component_role: str | None = Field(default=None, max_length=64)
    locale: Literal["en", "zh"] = "en"


@router.post("/extract")
def extract_source_ingestion(request: SourceIngestionExtractRequest) -> dict[str, object]:
    return extract_source_ingestion_payload(
        SourceIngestionExtractionInput(
            content=request.content,
            filename=request.filename,
            source_url=request.source_url,
            source_id=request.source_id,
            source_label=request.source_label,
            source_category=request.source_category,
            target_indicator_codes=request.target_indicator_codes,
            component_role=request.component_role,
            locale=request.locale,
        )
    )
