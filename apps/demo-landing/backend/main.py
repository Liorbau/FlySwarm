from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .models import SignupIn
from .storage import SignupRepository, get_repository

app = FastAPI(title="FlySwarm Landing Page API")


def get_repo() -> SignupRepository:
    return get_repository()


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check() -> dict[str, str]:
    """Lightweight liveness probe for uptime monitoring (e.g. Render/UptimeRobot).

    Handles GET and HEAD (HEAD-default monitors must get 200, not 404/501).
    Intentionally does no work: no storage, agent, or external calls — it only
    confirms the process is up and serving requests.
    """
    return {"status": "healthy"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/signup")
def signup(payload: SignupIn, repository: SignupRepository = Depends(get_repo)) -> dict[str, object]:
    try:
        record, created = repository.add_signup(payload.email)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save signup") from exc

    return {
        "status": "success",
        "created": created,
        "record": record.model_dump(),
    }


project_root = Path(__file__).resolve().parents[1]
frontend_dir = project_root / "frontend"

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
