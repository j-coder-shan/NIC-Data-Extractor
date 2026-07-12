"""Safe, privacy-conscious preprocessing for NIC image uploads."""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass
from os import getenv

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError


MIME_TYPE_ALIASES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
}
FORMAT_TO_MIME_TYPE = {"JPEG": "image/jpeg", "PNG": "image/png"}
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_DIMENSION = 2048
DEFAULT_MAX_PIXELS = 20_000_000


class ImagePreprocessingError(Exception):
    """Base class for input images that cannot safely be processed."""

    code = "image_preprocessing_error"


class UnsupportedImageError(ImagePreprocessingError):
    """Raised for formats outside JPEG and PNG, or MIME/content mismatches."""

    code = "unsupported_image"


class ImageTooLargeError(ImagePreprocessingError):
    """Raised when an upload exceeds byte or decoded pixel limits."""

    code = "image_too_large"


class CorruptedImageError(ImagePreprocessingError):
    """Raised when Pillow cannot verify and decode an image safely."""

    code = "corrupted_image"


@dataclass(frozen=True, slots=True)
class ImagePreprocessingSettings:
    """Limits and output controls for uploaded document images."""

    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES
    max_dimension: int = DEFAULT_MAX_DIMENSION
    max_pixels: int = DEFAULT_MAX_PIXELS
    jpeg_quality: int = 85
    blurry_threshold: float = 35.0

    @classmethod
    def from_environment(cls) -> "ImagePreprocessingSettings":
        """Read configurable limits while retaining production-safe defaults."""
        return cls(
            max_upload_size_bytes=int(
                getenv("MAX_UPLOAD_SIZE_BYTES", DEFAULT_MAX_UPLOAD_SIZE_BYTES)
            ),
            max_dimension=int(getenv("IMAGE_MAX_DIMENSION", DEFAULT_MAX_DIMENSION)),
            max_pixels=int(getenv("IMAGE_MAX_PIXELS", DEFAULT_MAX_PIXELS)),
        )


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """A verified, normalized image that is safe to send to Gemini."""

    data: bytes
    mime_type: str
    width: int
    height: int
    original_width: int
    original_height: int
    was_resized: bool
    blur_score: float
    is_blurry: bool


class ImagePreprocessor:
    """Validate, normalize, resize, and compress one NIC image in memory."""

    def __init__(self, settings: ImagePreprocessingSettings | None = None) -> None:
        self._settings = settings or ImagePreprocessingSettings.from_environment()
        self._validate_settings()

    def process(self, data: bytes, declared_mime_type: str) -> ProcessedImage:
        """Return a metadata-free JPEG or PNG image without writing it to disk."""
        if not data:
            raise CorruptedImageError("The uploaded image is empty")
        if len(data) > self._settings.max_upload_size_bytes:
            raise ImageTooLargeError("The uploaded image exceeds the configured size limit")

        expected_mime_type = self._normalize_mime_type(declared_mime_type)
        image, detected_mime_type = self._decode_image(data)
        if expected_mime_type != detected_mime_type:
            raise UnsupportedImageError(
                "The declared image MIME type does not match the image content"
            )

        original_width, original_height = image.size
        if original_width * original_height > self._settings.max_pixels:
            raise ImageTooLargeError("The decoded image exceeds the configured pixel limit")

        normalized, was_resized = self._resize(image)
        blur_score = self._calculate_blur_score(normalized)
        encoded = self._encode(normalized, detected_mime_type)

        return ProcessedImage(
            data=encoded,
            mime_type=detected_mime_type,
            width=normalized.width,
            height=normalized.height,
            original_width=original_width,
            original_height=original_height,
            was_resized=was_resized,
            blur_score=blur_score,
            is_blurry=blur_score < self._settings.blurry_threshold,
        )

    def _decode_image(self, data: bytes) -> tuple[Image.Image, str]:
        """Verify before decoding to reject corrupt data and decompression bombs."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as probe:
                    image_format = probe.format
                    probe.verify()

                mime_type = FORMAT_TO_MIME_TYPE.get(image_format or "")
                if mime_type is None:
                    raise UnsupportedImageError("Only PNG and JPEG images are supported")

                with Image.open(io.BytesIO(data)) as decoded:
                    decoded.load()
                    return decoded.copy(), mime_type
        except UnsupportedImageError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ImageTooLargeError("The uploaded image exceeds the configured pixel limit") from error
        except (OSError, UnidentifiedImageError, ValueError) as error:
            raise CorruptedImageError("The uploaded file is not a valid image") from error

    def _resize(self, image: Image.Image) -> tuple[Image.Image, bool]:
        """Downscale only when needed, preserving the original aspect ratio."""
        if max(image.size) <= self._settings.max_dimension:
            return image, False

        resized = image.copy()
        resized.thumbnail(
            (self._settings.max_dimension, self._settings.max_dimension),
            Image.Resampling.LANCZOS,
        )
        return resized, True

    def _encode(self, image: Image.Image, mime_type: str) -> bytes:
        """Re-encode in memory to remove metadata and efficiently compress pixels."""
        output = io.BytesIO()
        if mime_type == "image/jpeg":
            image.convert("RGB").save(
                output,
                format="JPEG",
                quality=self._settings.jpeg_quality,
                optimize=True,
                progressive=True,
            )
        else:
            image.save(output, format="PNG", optimize=True, compress_level=9)
        return output.getvalue()

    @staticmethod
    def _calculate_blur_score(image: Image.Image) -> float:
        """Return an edge-variance heuristic; lower scores indicate less detail."""
        grayscale = image.convert("L")
        if max(grayscale.size) > 512:
            grayscale.thumbnail((512, 512), Image.Resampling.LANCZOS)
        edge_image = grayscale.filter(ImageFilter.FIND_EDGES)
        return round(ImageStat.Stat(edge_image).var[0], 2)

    @staticmethod
    def _normalize_mime_type(declared_mime_type: str) -> str:
        """Accept browser JPEG aliases while rejecting every unsupported content type."""
        value = declared_mime_type.split(";", maxsplit=1)[0].strip().lower()
        mime_type = MIME_TYPE_ALIASES.get(value)
        if mime_type is None:
            raise UnsupportedImageError("Only image/png, image/jpeg, and image/jpg are supported")
        return mime_type

    def _validate_settings(self) -> None:
        """Fail fast for invalid configuration instead of weakening upload limits."""
        if self._settings.max_upload_size_bytes <= 0:
            raise ValueError("max_upload_size_bytes must be positive")
        if self._settings.max_dimension <= 0:
            raise ValueError("max_dimension must be positive")
        if self._settings.max_pixels <= 0:
            raise ValueError("max_pixels must be positive")
        if not 1 <= self._settings.jpeg_quality <= 95:
            raise ValueError("jpeg_quality must be between 1 and 95")
