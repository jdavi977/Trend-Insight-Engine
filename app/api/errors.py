from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def validation_exception_handler(request: Request, exception: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exception.errors()})


def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )
    # Preserve any headers the raiser attached — e.g. `Retry-After` /
    # `X-RateLimit-Reason` on the 429 abuse/cost guards (slice 2 §6, issue #59).
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": message},
        headers=getattr(exception, "headers", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, general_http_exception_handler)
