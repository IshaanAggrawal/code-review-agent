from app.workflow.context import GraphState
from app.integrations.llm.nvidia import NvidiaService
from app.domain.data_models import SecurityReview
from app.prompts.system_instructions import SECURITY_AGENT_PROMPT
from app.core.logger import logger


async def security_auditor_node(state: GraphState) -> dict:
    logger.info("[agent_security] Starting security review")
    llm = NvidiaService()

    result = await llm.complete_json(
        system_prompt=SECURITY_AGENT_PROMPT,
        user_message=f"Review this PR diff:\n\n{state['pr_diff_text']}",
    )

    review = SecurityReview(**result)
    logger.info(f"[agent_security] Score={review.score}/10 | Vulns={len(review.vulnerabilities)}")

    # Return ONLY what this agent owns
    return {"security_review": review}