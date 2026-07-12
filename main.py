from fastapi import FastAPI

from app.api.routes import router as api_router

app = FastAPI(
    title="NIC Data Extractor",
    description="AI-powered Sri Lankan NIC document intelligence API",
    version="0.1.0",
)


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {"message": "NIC Data Extractor API"}


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
