# NIC Data Extractor

An AI-powered document intelligence system for extracting and validating data from the front and back of Sri Lankan National Identity Cards (NICs). The application will use Gemini multimodal vision, Pydantic schemas, and NIC-specific validation rules rather than conventional OCR.

## Project status

The initial project architecture is in place. Extraction, validation, API, frontend, and test implementations will be delivered in focused milestones.

## Initial structure

```text
app/
  api/          # HTTP routers and request handling
  models/       # Pydantic schemas
  prompts/      # Gemini extraction prompts
  services/     # Gemini and image-processing services
  utils/        # Shared utilities
  validators/   # Sri Lankan NIC and cross-image rules
static/         # Frontend assets
templates/      # Server-rendered HTML templates
tests/          # Automated tests
uploads/        # Ephemeral runtime uploads (gitignored)
main.py         # FastAPI entry point
```

## Local startup

1. Create and activate a Python 3.12 virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and configure the values required by upcoming milestones.
4. Run `uvicorn main:app --reload`.

The application currently exposes `GET /health` and FastAPI documentation at `/docs`.
