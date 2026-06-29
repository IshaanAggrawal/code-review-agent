import json
import hashlib
import hmac
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.logger import logger

# We utilize JSONResponse directly to maintain explicit control over the HTTP response payload and structure,
# thereby bypassing standard FastAPI response modeling.
router = APIRouter()
settings = get_settings()


@router.post("/webhook")
async def github_webhook(request: Request):
    """
    Ingests and processes incoming GitHub webhook events.
    
    Execution Pipeline:
    1. Ingest the raw request body.
    2. Validate the cryptographic HMAC signature to authenticate the payload origin.
    3. Deserialize the JSON payload and extract routing metadata.
    4. Filter events, ensuring only pull request events proceed.
    5. Dispatch the review task to the asynchronous background worker queue.
    """

    # Stage 1: Ingest the raw request body.
    try:
        raw_body = await request.body()
    except Exception as e:
        logger.error(f"Failed to read body: {e}")
        return JSONResponse(status_code=400, content={"error": "Cannot read body"})

    # Stage 2: Validate the cryptographic HMAC signature to authenticate the payload origin.
    signature_header = request.headers.get("X-Hub-Signature-256", "")

    if signature_header:
        expected_sig = (
            "sha256="
            + hmac.new(
                settings.github_webhook_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(expected_sig, signature_header):
            logger.warning("Webhook signature mismatch")
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid signature"}
            )

    logger.info("Signature verified")

    # Stage 3: Deserialize the JSON payload.
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Stage 4: Extract routing metadata from HTTP headers.
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    action     = payload.get("action", "unknown")
    pr_number  = payload.get("number", 0)

    logger.info(f"Event received | type={event_type} | action={action} | PR=#{pr_number}")

    # Stage 5: Process lifecycle ping events used for webhook validation.
    if event_type == "ping":
        logger.info("GitHub ping — webhook connected successfully!")
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "Webhook connected! Ping received from GitHub."
            }
        )

    # Stage 6: Filter events, ensuring only pull request events proceed.
    if event_type != "pull_request":
        logger.info(f" Ignoring event: {event_type}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "ignored",
                "message": f"Event type '{event_type}' is not handled"
            }
        )

    # Stage 7: Restrict processing to relevant pull request lifecycle actions (opened, synchronized, reopened).
    if action not in ("opened", "synchronize", "reopened"):
        logger.info(f" Ignoring PR action: {action}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "ignored",
                "message": f"PR action '{action}' does not trigger review"
            }
        )

    # Stage 8: Dispatch the review task to the asynchronous background worker queue.
    logger.info(f"Triggering review for PR #{pr_number}")

    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job   = await redis.enqueue_job("run_pr_review", pr_number)
        await redis.aclose()

        logger.info(f"Job enqueued | job_id={job.job_id} | PR=#{pr_number}")

        return JSONResponse(
            status_code=202,
            content={
                "status":    "accepted",
                "message":   "Review job enqueued successfully",
                "pr_number": pr_number,
                "job_id":    job.job_id,
            }
        )

    except Exception as e:
        logger.error(f"Failed to enqueue job: {type(e).__name__}: {e}")

        # Return 200 OK to prevent GitHub from endlessly retrying the delivery mechanism.
        return JSONResponse(
            status_code=200,
            content={
                "status":    "received",
                "message":   "PR event received but job queue unavailable",
                "pr_number": pr_number,
                "error":     str(e),
            }
        )