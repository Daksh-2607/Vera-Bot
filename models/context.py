"""
Pydantic models for all context types and API schemas.
Mirrors the domain objects defined in challenge-brief.md §4.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# INCOMING API SCHEMAS
# ============================================================================

class ContextPushRequest(BaseModel):
    """POST /v1/context request body."""
    scope: Literal["category", "merchant", "customer", "trigger"]
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: str  # ISO 8601


class TickRequest(BaseModel):
    """POST /v1/tick request body."""
    now: str  # ISO 8601
    available_triggers: List[str] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    """POST /v1/reply request body."""
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: Literal["merchant", "customer"]
    message: str
    received_at: str  # ISO 8601
    turn_number: int


# ============================================================================
# OUTGOING API SCHEMAS
# ============================================================================

class ContextPushResponse(BaseModel):
    """POST /v1/context response (accepted)."""
    accepted: bool
    ack_id: str
    stored_at: str


class ContextPushErrorResponse(BaseModel):
    """POST /v1/context response (rejected)."""
    accepted: bool
    reason: Literal["stale_version", "invalid_scope", "malformed"]
    current_version: Optional[int] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """GET /v1/healthz response."""
    status: str
    uptime_seconds: int
    contexts_loaded: Dict[str, int]


class MetadataResponse(BaseModel):
    """GET /v1/metadata response."""
    team_name: str
    team_members: List[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str


class TickAction(BaseModel):
    """Single action in tick response."""
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: str
    template_params: List[str]
    body: str
    cta: Literal["open_ended", "yes_no", "none"]
    suppression_key: str
    rationale: str


class TickResponse(BaseModel):
    """POST /v1/tick response."""
    actions: List[TickAction]


class ReplySendAction(BaseModel):
    """POST /v1/reply response for 'send' action."""
    action: Literal["send"]
    body: str
    cta: Literal["open_ended", "yes_no", "none"]
    rationale: str


class ReplyWaitAction(BaseModel):
    """POST /v1/reply response for 'wait' action."""
    action: Literal["wait"]
    wait_seconds: int
    rationale: str


class ReplyEndAction(BaseModel):
    """POST /v1/reply response for 'end' action."""
    action: Literal["end"]
    rationale: str


# ============================================================================
# DOMAIN MODELS (INTERNAL)
# ============================================================================

class CategoryContext(BaseModel):
    """Represents a category's voice, offers, research, etc."""
    slug: str
    display_name: Optional[str] = None
    voice: Dict[str, Any]  # tone, vocab_allowed, vocab_taboo, etc.
    offer_catalog: List[Dict[str, Any]]
    peer_stats: Dict[str, Any]
    digest: List[Dict[str, Any]]
    patient_content_library: Optional[List[Dict[str, Any]]] = None
    seasonal_beats: Optional[List[Dict[str, Any]]] = None
    trend_signals: Optional[List[Dict[str, Any]]] = None


class MerchantContext(BaseModel):
    """Represents a specific merchant's state."""
    merchant_id: str
    category_slug: str
    identity: Dict[str, Any]
    subscription: Dict[str, Any]
    performance: Dict[str, Any]
    offers: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]]
    customer_aggregate: Dict[str, Any]
    signals: List[str]
    review_themes: Optional[List[Dict[str, Any]]] = None


class CustomerContext(BaseModel):
    """Represents a customer's relationship with a merchant."""
    customer_id: str
    merchant_id: str
    identity: Dict[str, Any]
    relationship: Dict[str, Any]
    state: str  # e.g., lapsed_soft, active, lapsed_hard
    preferences: Dict[str, Any]
    consent: Dict[str, Any]


class TriggerContext(BaseModel):
    """Represents an event that prompts messaging."""
    id: str
    scope: Literal["merchant", "customer"]
    kind: str
    source: Literal["external", "internal"]
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    payload: Dict[str, Any]
    urgency: int  # 1-5
    suppression_key: str
    expires_at: Optional[str] = None  # ISO 8601


# ============================================================================
# INTERNAL STATE MODELS
# ============================================================================

class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    turn_number: int
    from_role: Literal["vera", "merchant", "customer"]
    body: str
    received_at: str  # ISO 8601
    engagement_tag: Optional[str] = None  # e.g., "intent_action", "auto_reply"


class ConversationState(BaseModel):
    """Full state of an active conversation."""
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    trigger_id: Optional[str] = None
    turns: List[ConversationTurn]
    state: Literal["initiated", "awaiting_reply", "intent_action", "waiting", "ended", "escalated"]
    suppression_keys_used: List[str]
    last_action_at: Optional[str] = None  # ISO 8601
    waiting_until: Optional[str] = None  # ISO 8601 (if in waiting state)
