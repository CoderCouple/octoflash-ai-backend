import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Wrap every error response in the standard JSON envelope.

    Three handlers, in order of specificity:
      - HTTPException        → uses the raised status code and detail.
      - NotImplementedError  → 501 Not Implemented with a structured message.
                               Used by stubbed service bodies (planner, render
                               activities) so callers get JSON instead of
                               FastAPI's default plaintext.
      - Exception (catch-all)→ 500 Internal Server Error wrapped in the envelope;
                               full traceback logged for debugging.
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "result": None,
                "status_code": exc.status_code,
                "message": exc.detail,
                "success": False,
            },
        )

    @app.exception_handler(NotImplementedError)
    async def not_implemented_handler(request: Request, exc: NotImplementedError):
        logger.warning("NotImplementedError at %s %s: %s", request.method, request.url.path, exc)
        message = str(exc) or "This endpoint depends on a stubbed service."
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "result": None,
                "status_code": status.HTTP_501_NOT_IMPLEMENTED,
                "message": f"Not implemented: {message}",
                "success": False,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception at %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "result": None,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"{type(exc).__name__}: {exc}",
                "success": False,
            },
        )


class EntityNotFoundError(HTTPException):
    """Requested entity does not exist (or is soft-deleted). Returns 404."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type} with id '{entity_id}' not found",
        )


class InvalidStateTransitionError(HTTPException):
    """State-machine transition is not allowed. Returns 409."""

    def __init__(self, current_state: str, action: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot perform '{action}' from state '{current_state}'",
        )


class DuplicateEntityError(HTTPException):
    """Unique-constraint violation. Returns 409."""

    def __init__(self, entity_type: str, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity_type} with {field} '{value}' already exists",
        )


class RenderError(HTTPException):
    """Manim or FFmpeg render failed. Returns 500."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Render failed: {message}",
        )


class PlanLimitExceededError(HTTPException):
    """Org has reached its plan's limit for a resource. Returns 402."""

    def __init__(
        self, resource: str, current: int, maximum: int, plan: str
    ):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Plan '{plan}' limit reached for {resource}: "
                f"{current}/{maximum}. Upgrade to add more."
            ),
        )
