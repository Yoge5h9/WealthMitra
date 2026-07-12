from pathlib import Path

from fastapi import FastAPI

from app.api.aa import router as aa_router
from app.api.chat import router as chat_router
from app.api.customer import router as customer_router
from app.api.execute import router as execute_router
from app.api.health import router as health_router
from app.api.leads import router as leads_router
from app.api.nudges import router as nudges_router
from app.api.sessions import router as sessions_router
from app.api.spaces import router as spaces_router
from app.core.config import settings
from app.core.events import router as ws_router
from app.core.spaces import mount_spa

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(frontend_dist: Path | None = None) -> FastAPI:
    # Referencing `settings` here (rather than only in app/core/config.py) is what
    # makes an invalid provider/key combination surface as a startup failure.
    app = FastAPI(title="WealthMitra")
    app.state.settings = settings
    app.include_router(health_router, prefix="/api")
    app.include_router(spaces_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(leads_router, prefix="/api")
    app.include_router(execute_router, prefix="/api")
    app.include_router(aa_router, prefix="/api")
    app.include_router(customer_router, prefix="/api")
    app.include_router(nudges_router, prefix="/api")
    app.include_router(ws_router)
    mount_spa(app, dist_dir=frontend_dist if frontend_dist is not None else FRONTEND_DIST)
    return app


app = create_app()
