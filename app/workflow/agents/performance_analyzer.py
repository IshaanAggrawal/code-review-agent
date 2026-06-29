from app.workflow.context import GraphState
from app.integrations.llm.nvidia import NvidiaService
from app.domain.data_models import PerformanceReview
from app.prompts.system_instructions import PERFORMANCE_AGENT_PROMPT
from app.core.logger import logger


async def performance_analyzer_node(state: GraphState) -> dict:
    logger.info("[agent_performance] Starting performance review")
    llm = NvidiaService()

    result = await llm.complete_json(
        system_prompt=PERFORMANCE_AGENT_PROMPT,
        user_message=f"Review this PR diff:\n\n{state['pr_diff_text']}",
    )

    review = PerformanceReview(**result)
    logger.info(f"[agent_performance] Score={review.score}/10 | Issues={len(review.improvements)}")

    # Return ONLY what this agent owns
    return {"performance_review": review}