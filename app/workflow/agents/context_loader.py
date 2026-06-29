from app.workflow.context import GraphState
from app.integrations.github_client import GitHubService
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()


async def context_loader_node(state: GraphState) -> dict:
    pr_number      = state["pr_number"]
    repo_full_name = state.get("repo_full_name")

    target_repo = repo_full_name or (
        f"{settings.github_repo_owner}/{settings.github_repo_name}"
    )

    logger.info(f"[fetch_pr] PR=#{pr_number} | repo={target_repo}")

    github   = GitHubService()
    metadata = await github.get_pr_metadata(pr_number)
    files    = await github.get_pr_files(pr_number)

    # Build diff string for LLMs
    diff_parts = [
        f"PR #{metadata.pr_number}: {metadata.title}",
        f"Author: {metadata.author}",
        f"Branch: {metadata.head_branch} → {metadata.base_branch}",
        f"Files changed: {metadata.files_changed}",
        "=" * 60,
    ]
    for f in files:
        if f.patch:
            diff_parts.append(f"\n### File: {f.filename} ({f.status})")
            diff_parts.append(f.patch)

    diff_text = "\n".join(diff_parts)
    logger.info(f"[fetch_pr] Built diff | chars={len(diff_text)} | files={len(files)}")

    # Return only what fetch_pr owns
    return {
        "pr_metadata":  metadata,
        "pr_files":     files,
        "pr_diff_text": diff_text,
    }