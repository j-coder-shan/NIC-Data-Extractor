"""Gemini multimodal structured extraction service."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from typing import Any

from app.models.extraction import ExtractionSchema
from app.prompts.gemini_extraction import NIC_EXTRACTION_SYSTEM_INSTRUCTION


SUPPORTED_GEMINI_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png"})
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True, slots=True)
class GeminiImage:
    """An already-validated image payload supplied to Gemini."""

    data: bytes
    mime_type: str

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("Image data must not be empty")
        if self.mime_type not in SUPPORTED_GEMINI_IMAGE_MIME_TYPES:
            raise ValueError(f"Unsupported Gemini image MIME type: {self.mime_type}")


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    """Runtime configuration for the Gemini Developer API client."""

    api_key: str
    model: str = DEFAULT_GEMINI_MODEL

    @classmethod
    def from_environment(cls) -> "GeminiSettings":
        """Load the API key and model choice without exposing secrets in logs."""
        api_key = getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY is not configured")
        model = getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
        if not model:
            raise GeminiConfigurationError("GEMINI_MODEL must not be empty")
        return cls(api_key=api_key, model=model)


class GeminiServiceError(Exception):
    """Base class for safe, actionable Gemini integration failures."""

    code = "gemini_service_error"
    retryable = False


class GeminiConfigurationError(GeminiServiceError):
    """Raised when required Gemini configuration is missing or invalid."""

    code = "gemini_configuration_error"


class GeminiAuthenticationError(GeminiServiceError):
    """Raised when Gemini rejects the configured credentials."""

    code = "gemini_authentication_error"


class GeminiRateLimitError(GeminiServiceError):
    """Raised when Gemini temporarily rejects a request due to rate limiting."""

    code = "gemini_rate_limited"
    retryable = True


class GeminiTimeoutError(GeminiServiceError):
    """Raised when the upstream Gemini request times out."""

    code = "gemini_timeout"
    retryable = True


class GeminiStructuredOutputError(GeminiServiceError):
    """Raised when Gemini does not return the requested structured result."""

    code = "gemini_structured_output_error"


class GeminiExtractionService:
    """Extract NIC data from paired front and back images in one Gemini call."""

    def __init__(self, settings: GeminiSettings, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    def extract(self, *, front_image: GeminiImage, back_image: GeminiImage) -> ExtractionSchema:
        """Return structured extraction data for the two sides of one NIC."""
        from google.genai import types

        parts = [
            types.Part.from_text(text=NIC_EXTRACTION_SYSTEM_INSTRUCTION),
            types.Part.from_text(text="FRONT NIC IMAGE:"),
            types.Part.from_bytes(data=front_image.data, mime_type=front_image.mime_type),
            types.Part.from_text(text="BACK NIC IMAGE:"),
            types.Part.from_bytes(data=back_image.data, mime_type=back_image.mime_type),
        ]

        try:
            response = self._get_client().models.generate_content(
                model=self._settings.model,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractionSchema,
                    temperature=0,
                ),
            )
        except Exception as error:
            raise self._translate_error(error) from error

        parsed = getattr(response, "parsed", None)
        if parsed is None:
            raise GeminiStructuredOutputError("Gemini returned no structured extraction result")

        try:
            if isinstance(parsed, ExtractionSchema):
                return parsed
            return ExtractionSchema.model_validate(parsed)
        except Exception as error:
            raise GeminiStructuredOutputError(
                "Gemini returned a structured result that does not match the extraction schema"
            ) from error

    def _get_client(self) -> Any:
        """Create the SDK client lazily to keep configuration and tests explicit."""
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._settings.api_key)
        return self._client

    @staticmethod
    def _translate_error(error: Exception) -> GeminiServiceError:
        """Convert provider failures to stable application-level error categories."""
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if status_code in {401, 403}:
            return GeminiAuthenticationError("Gemini authentication failed")
        if status_code == 429:
            return GeminiRateLimitError("Gemini rate limit exceeded")
        if status_code in {408, 504} or isinstance(error, TimeoutError):
            return GeminiTimeoutError("Gemini request timed out")
        return GeminiServiceError("Gemini extraction request failed")
