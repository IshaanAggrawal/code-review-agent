from arq import ArqRedis
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()


async def run_pr_review(ctx: dict, pr_number: int, repo_full_name: str = None) -> dict:

    # ── Debug: print what settings worker actually loaded ──────────────────
    logger.info(f"[worker] Settings check:")
    logger.info(f"         GITHUB_REPO_OWNER = {settings.github_repo_owner}")
    logger.info(f"         GITHUB_REPO_NAME  = {settings.github_repo_name}")
    logger.info(f"         repo_full_name arg = {repo_full_name}")

    # ── Use repo from webhook payload, fall back to .env ──────────────────
    if not repo_full_name:
        repo_full_name = f"{settings.github_repo_owner}/{settings.github_repo_name}"

    logger.info(f"[worker] Final repo target: {repo_full_name}")
    logger.info(f"[worker] Starting review | PR=#{pr_number}")

    from app.workflow.orchestrator import review_graph
    from app.workflow.context import GraphState

    initial_state: GraphState = {
        "pr_number": pr_number,
        "repo_full_name": repo_full_name,
        "pr_metadata": None,
        "pr_files": None,
        "pr_diff_text": None,
        "quality_review": None,
        "security_review": None,
        "performance_review": None,
        "final_comment": None,
        "error": None,
        "messages": [],
    }

    try:
        final_state = await review_graph.ainvoke(initial_state)
        logger.info(f"[worker] Review completed | PR=#{pr_number}")
        return {"status": "completed", "pr_number": pr_number}
    except Exception as e:
        logger.error(f"[worker] Review failed | PR=#{pr_number} | error={e}")
        raise  # re-raise so ARQ shows full traceback


# ARQ worker settings
from arq.connections import RedisSettings
class WorkerSettings:
    # redis_settings = settings.redis_url
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [run_pr_review]
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per review