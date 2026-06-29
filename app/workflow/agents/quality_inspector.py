from app.workflow.context import GraphState
from app.integrations.llm.nvidia import NvidiaService
from app.domain.data_models import QualityReview
from app.prompts.system_instructions import QUALITY_AGENT_PROMPT
from app.core.logger import logger


async def quality_inspector_node(state: GraphState) -> dict:
    logger.info("[agent_quality] Starting code quality review")
    llm = NvidiaService()

    result = await llm.complete_json(
        system_prompt=QUALITY_AGENT_PROMPT,
        user_message=f"Review this PR diff:\n\n{state['pr_diff_text']}",
    )

    review = QualityReview(**result)
    logger.info(f"[agent_quality] Score={review.score}/10 | Issues={len(review.issues)}")

    # Return ONLY what this agent owns — not {**state}
    return {"quality_review": review}