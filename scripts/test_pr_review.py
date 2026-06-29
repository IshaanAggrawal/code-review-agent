"""
Local integration test for the Aegis code review pipeline.
Simulates a GitHub Pull Request event and executes the agentic review graph
offline (mocking GitHub API interactions but keeping live LLM calls).
"""
import asyncio
import json
from langgraph.graph import StateGraph, END

from app.workflow.context import GraphState
from app.domain.data_models import PRMetadata, PRFile
from app.workflow.agents.quality_inspector import quality_inspector_node
from app.workflow.agents.security_auditor import security_auditor_node
from app.workflow.agents.performance_analyzer import performance_analyzer_node
from app.prompts.system_instructions import REVIEWER_AGENT_PROMPT
from app.integrations.llm.nvidia import NvidiaService
from app.integrations.llm.claude import ClaudeService
from app.core.config import get_settings


async def mock_context_loader(state: GraphState) -> dict:
    """Simulates fetching metadata and code diffs for a pull request."""
    print("[Mock Loader] Simulating PR diff extraction...")
    return {
        "pr_metadata": PRMetadata(
            pr_number=42,
            title="Optimize User Database Ingestion and Key Management",
            author="developer-one",
            base_branch="main",
            head_branch="feature/optimize-ingestion",
            repo_full_name="enterprise/aegis-app",
            files_changed=1,
            additions=21,
            deletions=0,
            pr_url="https://github.com/enterprise/aegis-app/pull/42"
        ),
        "pr_files": [
            PRFile(
                filename="scripts/sample_code.py",
                status="added",
                additions=21,
                deletions=0,
                patch=(
                    "+ import os\n"
                    "+ import sqlite3\n"
                    "+ \n"
                    "+ # Hardcoded secret\n"
                    "+ API_KEY = \"sk-prod-supersecretkey123\"\n"
                    "+ \n"
                    "+ def get_user(user_id):\n"
                    "+     conn = sqlite3.connect(\"users.db\")\n"
                    "+     # SQL injection vulnerability\n"
                    "+     query = f\"SELECT * FROM users WHERE id = {user_id}\"\n"
                    "+     result = conn.execute(query)\n"
                    "+     return result\n"
                    "+ \n"
                    "+ def process_users(users):\n"
                    "+     # N+1 problem\n"
                    "+     for user in users:\n"
                    "+         for item in users:      # Nested loop — O(n²)\n"
                    "+             print(user, item)\n"
                    "+ \n"
                    "+ def x(a, b, c, d, e):          # Bad naming\n"
                    "+     return a+b+c+d+e"
                )
            )
        ],
        "pr_diff_text": (
            "diff --git a/scripts/sample_code.py b/scripts/sample_code.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/scripts/sample_code.py\n"
            "@@ -0,0 +1,21 @@\n"
            "+ import os\n"
            "+ import sqlite3\n"
            "+ \n"
            "+ # Hardcoded secret\n"
            "+ API_KEY = \"sk-prod-supersecretkey123\"\n"
            "+ \n"
            "+ def get_user(user_id):\n"
            "+     conn = sqlite3.connect(\"users.db\")\n"
            "+     # SQL injection vulnerability\n"
            "+     query = f\"SELECT * FROM users WHERE id = {user_id}\"\n"
            "+     result = conn.execute(query)\n"
            "+     return result\n"
            "+ \n"
            "+ def process_users(users):\n"
            "+     # N+1 problem\n"
            "+     for user in users:\n"
            "+         for item in users:      # Nested loop — O(n²)\n"
            "+             print(user, item)\n"
            "+ \n"
            "+ def x(a, b, c, d, e):          # Bad naming\n"
            "+     return a+b+c+d+e"
        )
    }


async def mock_reviewer_node(state: GraphState) -> dict:
    """Simulates the final reviewer agent without posting back to GitHub."""
    print("[Mock Reviewer] Synthesizing final review report...")
    settings = get_settings()
    
    # Initialize the correct LLM provider configured in the environment
    llm = NvidiaService() if settings.nvidia_api_key else ClaudeService()
    
    combined = json.dumps({
        "quality": state["quality_review"].model_dump() if state["quality_review"] else {},
        "security": state["security_review"].model_dump() if state["security_review"] else {},
        "performance": state["performance_review"].model_dump() if state["performance_review"] else {},
        "pr_title": state["pr_metadata"].title,
        "pr_author": state["pr_metadata"].author,
    }, indent=2)
    
    final_comment = await llm.complete(
        system_prompt=REVIEWER_AGENT_PROMPT,
        user_message=f"Generate the final review comment:\n\n{combined}",
    )
    return {"final_comment": final_comment}


async def main():
    # Build local testing graph
    graph = StateGraph(GraphState)
    graph.add_node("fetch_pr", mock_context_loader)
    graph.add_node("agent_quality", quality_inspector_node)
    graph.add_node("agent_security", security_auditor_node)
    graph.add_node("agent_performance", performance_analyzer_node)
    graph.add_node("agent_reviewer", mock_reviewer_node)
    
    graph.set_entry_point("fetch_pr")
    graph.add_edge("fetch_pr", "agent_quality")
    graph.add_edge("fetch_pr", "agent_security")
    graph.add_edge("fetch_pr", "agent_performance")
    
    graph.add_edge("agent_quality", "agent_reviewer")
    graph.add_edge("agent_security", "agent_reviewer")
    graph.add_edge("agent_performance", "agent_reviewer")
    graph.add_edge("agent_reviewer", END)
    
    compiled_graph = graph.compile()
    
    print("--------------------------------------------------")
    print("Initializing Offline Aegis Code Review Workflow...")
    print("--------------------------------------------------")
    
    initial_state = {
        "pr_number": 42,
        "repo_full_name": "enterprise/aegis-app"
    }
    
    result = await compiled_graph.ainvoke(initial_state)
    
    print("\n" + "="*20 + " FINAL GENERATED COMMENT " + "="*20)
    comment = str(result.get("final_comment", ""))
    print(comment.encode("ascii", "ignore").decode("ascii"))
    print("="*65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
