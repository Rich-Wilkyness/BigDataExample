"""Small HTTP entry point used by the CI/CD container exercise."""

from fastapi import FastAPI

from big_data_example import __version__


app = FastAPI(title="BigDataExample", version=__version__)


@app.get("/")
def home() -> dict[str, str]:
    """Describe the application and deployed package version."""
    return {
        "application": "BigDataExample",
        "version": __version__,
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the API process is ready to accept requests."""
    return {"status": "healthy"}
