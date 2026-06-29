import json
from app.workflow.context import GraphState
from app.integrations.llm.nvidia import NvidiaService
from app.integrations.github_client import GitHubService
from app.prompts.system_instructions import REVIEWER_AGENT_PROMPT
from app.core.logger import logger


async def review_synthesizer_node(state: GraphState) -> dict:
    logger.info("[agent_reviewer] Synthesizing final review")
    llm = NvidiaService()

    combined = json.dumps({
        "quality":     state["quality_review"].model_dump(),
        "security":    state["security_review"].model_dump(),
        "performance": state["performance_review"].model_dump(),
        "pr_title":    state["pr_metadata"].title,
        "pr_author":   state["pr_metadata"].author,
    }, indent=2)

    final_comment = await llm.complete(
        system_prompt=REVIEWER_AGENT_PROMPT,
        user_message=f"Generate the final review comment:\n\n{combined}",
    )

    # Post to GitHub
    github = GitHubService()
    await github.post_review_comment(
        pr_number=state["pr_number"],
        comment=final_comment,
    )

    logger.info(f"[agent_reviewer] Comment posted | PR=#{state['pr_number']}")

    # Return only what reviewer owns
    return {"final_comment": final_comment}