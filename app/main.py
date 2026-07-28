import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import errors, health, runs

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
        # `Retry-After` / `X-RateLimit-Reason` are non-safelisted response headers;
        # the browser hides them from JS unless explicitly exposed. The New Run
        # page reads them to render distinct, friendly 429 messages with a
        # retry-after hint (spec §9.3, issue #64). Without this the body still
        # carries a friendly detail, but the precise reason/timer is unreadable.
        expose_headers=["Retry-After", "X-RateLimit-Reason", "X-RateLimit-Window"],
    )

    # Spec §6 / §10: keep run pages out of search indexes. Middleware (not a
    # per-route header) so /runs/:id and /runs/:id/approve inherit it.
    @app.middleware("http")
    async def add_x_robots_tag(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/runs"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    app.include_router(health.router)
    app.include_router(runs.router)

    errors.register_exception_handlers(app)

    return app


app = create_app()
