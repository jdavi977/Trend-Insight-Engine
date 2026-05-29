import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import appstore, errors, home, insights, internal, runs, youtube

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("api")


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Spec §6 / §10: keep run pages out of search indexes. Middleware (not a
    # per-route header) so /runs/:id/approve, feedback, report etc. inherit it.
    @app.middleware("http")
    async def add_x_robots_tag(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/runs"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    app.include_router(youtube.router)
    app.include_router(appstore.router)
    app.include_router(home.router)
    app.include_router(internal.router)
    app.include_router(insights.router)
    app.include_router(runs.router)

    errors.register_exception_handlers(app)

    return app


app = create_app()
