"""Schemas for Gemini's structured NIC extraction result."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import ExtractedField


NIC_DOCUMENT_TYPE = "Sri Lankan National Identity Card"


class ExtractionSchema(BaseModel):
    """Information extracted jointly from the front and back NIC images."""

    model_config = ConfigDict(extra="forbid")

    document_type: Literal["Sri Lankan National Identity Card"] | None = Field(
        default=None,
        description="Detected document type, or null when the uploads are not a Sri Lankan NIC.",
    )
    nic_number: ExtractedField
    nic_type: ExtractedField
    full_name: ExtractedField
    date_of_birth: ExtractedField
    gender: ExtractedField
    address: ExtractedField
    place_of_birth: ExtractedField
    date_of_issue: ExtractedField
    is_same_document: bool | None = Field(
        default=None,
        description="Whether both images appear to show the same physical NIC.",
    )
    same_document_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in the cross-image document match decision.",
    )
    overall_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in the complete extraction result.",
    )
