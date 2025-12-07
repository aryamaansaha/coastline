"""
Session schemas for HITL (Human-in-the-Loop) workflow.

Sessions track the state of trip generation across multiple request/response cycles.
"""

from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from enum import Enum

from app.schemas.trip import Itinerary, CostBreakdown


class SessionStatus(str, Enum):
    """Status of a trip generation session"""
    PROCESSING = "processing"           # Agent is running
    AWAITING_APPROVAL = "awaiting_approval"  # HITL checkpoint - waiting for human
    COMPLETE = "complete"               # Approved and finalized
    FAILED = "failed"                   # Agent failed after retries
    EXPIRED = "expired"                 # Session timed out (24h)


class HumanDecision(BaseModel):
    """Human decision at HITL checkpoint"""
    action: Literal["approve", "revise"]
    feedback: str | None = None  # Required if action == "revise"
    new_budget: float | None = None  # Optional budget adjustment


class SessionPreview(BaseModel):
    """Preview data shown at HITL checkpoint"""
    itinerary: Itinerary
    total_cost: float
    cost_breakdown: CostBreakdown
    budget_limit: float  # Current budget (may have been updated)
    budget_status: Literal["under", "over", "unknown"]
    revision_count: int  # How many times user has requested revision


class TripSession(BaseModel):
    """Full session state stored in MongoDB"""
    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime  # For 24h TTL cleanup
    
    # User preferences (may be updated with new_budget)
    preferences: dict
    
    # Preview data (populated when awaiting_approval)
    preview: SessionPreview | None = None
    
    # Final result (populated when complete)
    final_itinerary: Itinerary | None = None
    final_cost: float | None = None
    final_breakdown: CostBreakdown | None = None
    
    # Error info (if failed)
    error_message: str | None = None


# ============================================================================
# SSE EVENT SCHEMAS
# ============================================================================

class SSEEventType(str, Enum):
    """Types of SSE events sent during generation"""
    STATUS = "status"                   # Progress update
    TOOL_CALL = "tool_call"             # Agent calling a tool
    TOOL_RESULT = "tool_result"         # Tool returned result
    AWAITING_APPROVAL = "awaiting_approval"  # HITL checkpoint reached
    COMPLETE = "complete"               # Generation finished
    ERROR = "error"                     # Something went wrong


class SSEStatusEvent(BaseModel):
    """Status update event"""
    event: Literal["status"] = "status"
    step: str  # e.g., "searching_flights", "generating_itinerary"
    message: str


class SSEToolCallEvent(BaseModel):
    """Tool call event"""
    event: Literal["tool_call"] = "tool_call"
    tool_name: str
    args: dict


class SSEToolResultEvent(BaseModel):
    """Tool result event"""
    event: Literal["tool_result"] = "tool_result"
    tool_name: str
    result_summary: str  # Brief summary, not full result


class SSEAwaitingApprovalEvent(BaseModel):
    """HITL checkpoint event"""
    event: Literal["awaiting_approval"] = "awaiting_approval"
    session_id: str
    preview: SessionPreview


class SSECompleteEvent(BaseModel):
    """Generation complete event"""
    event: Literal["complete"] = "complete"
    session_id: str
    itinerary: Itinerary
    total_cost: float
    cost_breakdown: CostBreakdown


class SSEErrorEvent(BaseModel):
    """Error event"""
    event: Literal["error"] = "error"
    message: str
    recoverable: bool = False

