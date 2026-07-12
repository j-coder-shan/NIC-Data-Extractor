"""Top-level success and failure payloads for the public API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.extraction import ExtractionSchema
from app.models.validation import ValidationSchema


class ErrorDetail(BaseModel):
    """A client-safe error suitable for API responses."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Stable, machine-readable error code.")
    message: str = Field(description="Human-readable description of the error.")
    field: str | None = Field(default=None, description="Related request field, if any.")


class ExtractionResponse(BaseModel):
    """Production API payload for an extraction request."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: ExtractionSchema
    validation: ValidationSchema
    warnings: list[str] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
    processing_time_ms: int = Field(ge=0)


class ErrorResponse(BaseModel):
    """Production API payload for rejected or failed requests."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[False] = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(min_length=1)
    processing_time_ms: int | None = Field(default=None, ge=0)
