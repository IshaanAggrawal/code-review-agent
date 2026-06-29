"""
Data transfer objects and domain models.
Utilizes Pydantic to ensure strict validation of inputs, agent outputs, and external payloads.
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.domain.constants import ReviewStatus, AgentType, IssueSeverity


class PRMetadata(BaseModel):
    """
    Metadata associated with a GitHub Pull Request.
    Provides fundamental context necessary for fetching target diffs and contextualizing the review.
    """
    pr_number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    repo_full_name: str
    files_changed: int
    additions: int
    deletions: int
    pr_url: str


class PRFile(BaseModel):
    """
    Represents a single file modification within a Pull Request.
    Encapsulates line additions, deletions, and the raw patch diff.
    """
    filename: str
    status: str                  # added, modified, removed
    additions: int
    deletions: int
    patch: Optional[str] = None  # The actual diff


class CodeIssue(BaseModel):
    """
    A discrete finding identified by a specialized review agent.
    Captures exact file locations, severity classification, and remediation advice.
    """
    file: str
    line: Optional[int] = None
    severity: IssueSeverity
    description: str
    suggestion: str


class QualityReview(BaseModel):
    """
    Aggregated analysis produced by the Quality Inspector agent.
    Rates overall maintainability and lists specific structural defects.
    """
    score: int = Field(..., ge=0, le=10, description="Code quality score 0-10")
    issues: list[CodeIssue] = []
    summary: str
    passed: bool


class SecurityReview(BaseModel):
    """
    Aggregated analysis produced by the Security Auditor agent.
    Identifies vulnerabilities, unsafe patterns, and potential exposure risks.
    """
    score: int = Field(..., ge=0, le=10)
    vulnerabilities: list[CodeIssue] = []
    summary: str
    passed: bool


class PerformanceReview(BaseModel):
    """
    Aggregated analysis produced by the Performance Analyzer agent.
    Highlights computational inefficiencies and optimization opportunities.
    """
    score: int = Field(..., ge=0, le=10)
    improvements: list[CodeIssue] = []
    summary: str
    passed: bool


class GitHubWebhookPayload(BaseModel):
    """
    Partial schema definition for incoming GitHub webhook payloads.
    Provides validation strictly for the routing and dispatching fields required by the event router.
    """
    action: str
    number: int
    pull_request: dict


class ReviewJobResponse(BaseModel):
    """
    API payload returned to callers upon successfully dispatching a review job to the queue.
    """
    job_id: str
    pr_number: int
    status: ReviewStatus
    message: str