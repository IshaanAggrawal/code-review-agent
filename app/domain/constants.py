"""
Domain constants and enumerations.
Provides strict, type-safe definitions for categorical data across the application.
"""
from enum import Enum


class ReviewStatus(str, Enum):
    """Represents the lifecycle state of a code review background job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Defines the specialized agent personas operating within the workflow."""
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    REVIEWER = "reviewer"


class IssueSeverity(str, Enum):
    """Categorizes the severity of findings identified during static or dynamic analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
