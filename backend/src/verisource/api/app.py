"""FastAPI shell with redacted errors; run uvicorn verisource.api.app:app on loopback."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from verisource.api.errors import http_error, unexpected_error, validation_error
from verisource.config import Settings, disable_external_tracing
from verisource.db.session import create_database_engine
from verisource.observability import record_request
from verisource.security.sessions import AuthenticationState


def create_app(settings: Settings | None = None) -> FastAPI:
    disable_external_tracing()
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(settings)
        application.state.engine = engine
        application.state.settings = settings
        application.state.authentication = AuthenticationState()
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="VeriSource local core", lifespan=lifespan, debug=False)
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"]
    )
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(RequestValidationError, validation_error)
    application.add_exception_handler(Exception, unexpected_error)
    from verisource.api.actions import router as actions_router
    from verisource.api.assessments import router as assessments_router
    from verisource.api.auth import router as auth_router
    from verisource.api.cases import router as cases_router
    from verisource.api.checklists import router as checklists_router
    from verisource.api.documents import router as documents_router
    from verisource.api.events import router as events_router
    from verisource.api.evidence import router as evidence_router
    from verisource.api.runs import router as runs_router

    for router in (
        auth_router,
        cases_router,
        checklists_router,
        runs_router,
        documents_router,
        actions_router,
        events_router,
        assessments_router,
        evidence_router,
    ):
        application.include_router(router)

    @application.middleware("http")
    async def correlation(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        raw_id = request.headers.get("X-Request-ID", "")
        try:
            request_id = str(UUID(raw_id))
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 -- keep private exceptions out of server logs.
            response = await unexpected_error(request, exc)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        record_request(request_id, request.method, response.status_code)
        return response

    @application.get("/health/live")
    @application.get("/api/v1/health/live")
    def live() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/health/ready", status_code=503)
    @application.get("/api/v1/health/ready", status_code=503)
    def ready(response: Response) -> dict[str, str]:
        from verisource.operations.preflight import preflight

        available = bool(preflight(settings)["ready"]) if settings.ollama_digest else False
        response.status_code = 200 if available else 503
        return {"status": "ready" if available else "not_ready"}

    return application


app = create_app()
