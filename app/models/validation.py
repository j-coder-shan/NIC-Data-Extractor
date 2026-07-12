"""Schemas for NIC-specific and cross-image validation reports."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class NICFormat(str, Enum):
    """Sri Lankan NIC numbering formats supported by the validator."""

    OLD = "old"
    NEW = "new"
    UNKNOWN = "unknown"


class NICValidationSchema(BaseModel):
    """Results from decoding and validating the extracted NIC number."""

    model_config = ConfigDict(extra="forbid")

    nic_valid: bool = False
    nic_format: NICFormat = NICFormat.UNKNOWN
    decoded_date_of_birth: date | None = None
    decoded_gender: str | None = None
    dob_matches: bool | None = None
    gender_matches: bool | None = None
    messages: list[str] = Field(default_factory=list)


class CrossImageValidationSchema(BaseModel):
    """Validation facts that require both uploaded images."""

    model_config = ConfigDict(extra="forbid")

    front_uploaded: bool
    back_uploaded: bool
    same_document: bool | None = None
    document_complete: bool = False
    messages: list[str] = Field(default_factory=list)


class ValidationSchema(BaseModel):
    """Complete validation report returned with a successful extraction."""

    model_config = ConfigDict(extra="forbid")

    nic: NICValidationSchema
    cross_image: CrossImageValidationSchema
