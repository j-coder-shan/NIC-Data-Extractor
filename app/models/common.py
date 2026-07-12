"""Shared Pydantic types used by extraction and API response schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentSide(str, Enum):
    """The image side that supplied a grounded extracted value."""

    FRONT = "front"
    BACK = "back"
    BOTH = "both"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """Normalized [0, 1] coordinates for visible evidence in an image."""

    model_config = ConfigDict(extra="forbid")

    x1: float = Field(ge=0, le=1, description="Left coordinate.")
    y1: float = Field(ge=0, le=1, description="Top coordinate.")
    x2: float = Field(ge=0, le=1, description="Right coordinate.")
    y2: float = Field(ge=0, le=1, description="Bottom coordinate.")

    @field_validator("x2")
    @classmethod
    def right_must_follow_left(cls, value: float, info) -> float:
        """Reject inverted horizontal coordinates."""
        left = info.data.get("x1")
        if left is not None and value < left:
            raise ValueError("x2 must be greater than or equal to x1")
        return value

    @field_validator("y2")
    @classmethod
    def bottom_must_follow_top(cls, value: float, info) -> float:
        """Reject inverted vertical coordinates."""
        top = info.data.get("y1")
        if top is not None and value < top:
            raise ValueError("y2 must be greater than or equal to y1")
        return value


class ExtractedField(BaseModel):
    """A visible text value and the evidence that supports it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str | None = Field(
        default=None,
        description="Visible extracted value, or null when the model is uncertain.",
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Model confidence in this field, from 0 to 1.",
    )
    bbox: BoundingBox | None = Field(
        default=None,
        description="Normalized bounding box of the source evidence when available.",
    )
    source_side: DocumentSide = Field(
        default=DocumentSide.UNKNOWN,
        description="NIC image side from which the value was obtained.",
    )
