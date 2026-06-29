"""
Centralized exception taxonomy for the application.
Provides structured, domain-specific exception classes to ensure consistent error handling
and detailed telemetry across all components.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class AegisBaseException(Exception):
    """
    Base exception class from which all application-specific exceptions inherit.
    Encapsulates the standard HTTP status code mapping and error messaging.
    """
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class GitHubAPIException(AegisBaseException):
    """Raised when interactions with the GitHub API fail, due to network issues or invalid responses."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(f"GitHub API error: {message}", status_code)


class PRNotFoundException(AegisBaseException):
    def __init__(self, pr_number: int):
        super().__init__(f"PR #{pr_number} not found", status_code=404)


class AgentExecutionException(AegisBaseException):
    def __init__(self, agent_name: str, reason: str):
        super().__init__(
            f"Agent '{agent_name}' failed: {reason}", status_code=500
        )


class LLMResponseParseException(AegisBaseException):
    def __init__(self, agent_name: str, raw_response: str):
        self.raw_response = raw_response
        super().__init__(
            f"Agent '{agent_name}' returned unparseable JSON", status_code=500
        )


class WebhookVerificationException(AegisBaseException):
    def __init__(self):
        super().__init__("Webhook signature verification failed", status_code=403)


class WorkerJobException(AegisBaseException):
    def __init__(self, job_id: str, reason: str):
        super().__init__(f"Worker job '{job_id}' failed: {reason}", status_code=500)


async def global_exception_handler(
    request: Request, exc: AegisBaseException
) -> JSONResponse:
    """
    Global exception interceptor for FastAPI requests.
    Translates unhandled `AegisBaseException` instances into structured JSON HTTP responses
    while emitting appropriate telemetry for the error.
    """
    logger.error(
        f"Handled exception | path={request.url.path} | "
        f"type={type(exc).__name__} | message={exc.message}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": type(exc).__name__,
            "message": exc.message,
            "path": str(request.url.path),
        },
    )