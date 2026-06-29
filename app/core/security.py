import hashlib
import hmac
from fastapi import Request, HTTPException, status
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()


async def verify_github_signature(request: Request) -> bytes:
    """
    Verifies GitHub webhook HMAC-SHA256 signature.
    GitHub signs every webhook payload — we MUST verify
    before processing to prevent spoofed requests.
    """
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not signature_header:
        logger.warning("Webhook received without signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    raw_body = await request.body()
    expected_sig = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
    )
    if not hmac.compare_digest(expected_sig, signature_header):
        logger.error("Webhook signature mismatch — possible spoofed request")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )

    logger.debug("Webhook signature verified successfully")
    return raw_body