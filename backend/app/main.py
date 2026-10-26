"""HTTP entry point for the minimal CareerPilot API."""

from fastapi import FastAPI

app = FastAPI(
    title="CareerPilot API",
    description="Learning foundation API; not production-secure.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report that this API process is responding."""

    return {"status": "ok"}
