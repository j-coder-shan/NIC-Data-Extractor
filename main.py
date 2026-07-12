"""Application entry point for the NIC Document Intelligence API."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="NIC Data Extractor",
    description="AI-powered Sri Lankan National Identity Card document intelligence.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a lightweight readiness response for local and deployed environments."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> str:
    """Serve a temporary application landing page until the UI milestone."""
    return (
        "<main><h1>NIC Data Extractor</h1>"
        "<p>The document intelligence API is being prepared.</p>"
        '<p><a href="/docs">Open API documentation</a></p></main>'
    )
