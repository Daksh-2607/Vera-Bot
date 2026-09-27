"""
MagicPin Vera AI Challenge — FastAPI Application

Main entry point implementing all 5 required endpoints:
1. POST /v1/context — receive context
2. POST /v1/tick — proactive outreach
3. POST /v1/reply — handle merchant replies
4. GET /v1/healthz — liveness probe
5. GET /v1/metadata — bot identity
"""

import os
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import json
import uuid

from models.context import (
    ContextPushRequest, ContextPushResponse, ContextPushErrorResponse,
    TickRequest, TickResponse, TickAction,
    ReplyRequest, ReplySendAction, ReplyWaitAction, ReplyEndAction,
    HealthResponse, MetadataResponse
)
from engine.context_store import get_store
from engine.conversation import get_manager
from engine.trigger_ranker import select_top_trigger
from engine.composer import MessageComposer
from engine.intent import recognize_intent, is_auto_reply
from engine.consent import has_consent

# ============================================================================
# CONFIGURATION
# ============================================================================

TEAM_NAME = os.environ.get("TEAM_NAME", "Vera Team")
TEAM_MEMBERS = os.environ.get("TEAM_MEMBERS", "Claude").split(",")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "vera@magicpin.ai")
BOT_VERSION = os.environ.get("BOT_VERSION", "1.0.0")
SUBMITTED_AT = os.environ.get("SUBMITTED_AT", datetime.utcnow().isoformat() + "Z")

# ============================================================================
# INITIALIZATION
# ============================================================================

app = FastAPI(title="Vera AI Merchant Assistant", version=BOT_VERSION)
START_TIME = time.time()

store = get_store()
conv_manager = get_manager()
composer = MessageComposer(use_llm=False)  # Can be enabled later

# ============================================================================
# MIDDLEWARE & LOGGING
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    # Could log to structured logging system here
    return response


# ============================================================================
# ENDPOINT 1: POST /v1/context
# ============================================================================

@app.post("/v1/context", response_model=ContextPushResponse)
async def push_context(body: ContextPushRequest):
    """
    Receive new or updated context from the judge.
    
    Handles:
    - Category updates
    - Merchant state changes
    - Customer data
    - Trigger events
    
    Implements idempotent versioning.
    """
    # Push to store
    accepted, reason, current_version = store.push(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload,
        delivered_at=body.delivered_at
    )
    
    if not accepted:
        if reason == "stale_version":
            return JSONResponse(
                status_code=409,
                content={
                    "accepted": False,
                    "reason": "stale_version",
                    "current_version": current_version
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "accepted": False,
                    "reason": reason,
                    "details": f"Invalid scope: {body.scope}"
                }
            )
    
    return ContextPushResponse(
        accepted=True,
        ack_id=f"ack_{body.context_id}_v{body.version}",
        stored_at=datetime.utcnow().isoformat() + "Z"
    )


# ============================================================================
# ENDPOINT 2: POST /v1/tick
# ============================================================================

@app.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickRequest):
    """
    Periodic wake-up call. Bot decides what proactive messages to send.
    
    For each available trigger:
    1. Rank by priority
    2. Select top trigger
    3. Load category, merchant, trigger contexts
    4. Compose message
    5. Add to actions
    
    Returns list of actions to send.
    """
    actions = []
    
    if not body.available_triggers:
        return TickResponse(actions=[])
    
    # Select the top priority trigger
    top_trigger_id = select_top_trigger(body.available_triggers)
    if not top_trigger_id:
        return TickResponse(actions=[])
    
    # Load trigger context
    trigger_ctx = store.get("trigger", top_trigger_id)
    if not trigger_ctx:
        return TickResponse(actions=[])
    
    trigger_payload = trigger_ctx.payload
    merchant_id = trigger_payload.get("merchant_id")
    customer_id = trigger_payload.get("customer_id")
    
    # Load merchant and category
    merchant_ctx = store.get("merchant", merchant_id) if merchant_id else None
    if not merchant_ctx:
        return TickResponse(actions=[])
    
    category_slug = merchant_ctx.payload.get("category_slug")
    category_ctx = store.get("category", category_slug) if category_slug else None
    if not category_ctx:
        return TickResponse(actions=[])
    
    # Check customer consent if this is customer-scoped
    if trigger_payload.get("scope") == "customer" and customer_id:
        customer_ctx = store.get("customer", customer_id)
        if not customer_ctx:
            return TickResponse(actions=[])
        
        # Determine action type from trigger kind
        action_type = "recall_reminders"  # Default
        if "appointment" in trigger_payload.get("kind", ""):
            action_type = "appointment_reminders"
        elif "promotional" in trigger_payload.get("kind", ""):
            action_type = "promotional_offers"
        
        if not has_consent(customer_ctx.payload, action_type):
            # No consent, skip
            return TickResponse(actions=[])
    
    # Compose message
    result = composer.compose(
        category_slug=category_slug,
        merchant_id=merchant_id,
        trigger_id=top_trigger_id,
        customer_id=customer_id
    )
    
    if not result:
        return TickResponse(actions=[])
    
    # Check for repetition
    if trigger_payload.get("scope") == "merchant":
        # Check recent conversations for this merchant
        recent_conversations = [c for c in conv_manager.all_conversations() if c.merchant_id == merchant_id]
        if recent_conversations:
            # If we already sent this exact message, skip
            for conv in recent_conversations:
                if conv.has_repeated_message(result.get("body", "")):
                    return TickResponse(actions=[])
    
    # Create conversation
    conversation_id = f"conv_{merchant_id}_{top_trigger_id}_{uuid.uuid4().hex[:8]}"
    conv_state = conv_manager.create(
        conversation_id=conversation_id,
        merchant_id=merchant_id,
        customer_id=customer_id,
        trigger_id=top_trigger_id
    )
    
    # Track suppression key
    suppression_key = trigger_ctx.payload.get("suppression_key", "")
    if suppression_key:
        conv_manager.add_suppression_key(conversation_id, suppression_key)
    
    # Add Vera's message to conversation history
    conv_manager.add_vera_message(conversation_id, result.get("body", ""), body.now)
    
    # Build action
    action = TickAction(
        conversation_id=conversation_id,
        merchant_id=merchant_id,
        customer_id=customer_id,
        send_as="merchant_on_behalf" if customer_id else "vera",
        trigger_id=top_trigger_id,
        template_name=result.get("template_name", "generic_v1"),
        template_params=result.get("template_params", []),
        body=result.get("body", ""),
        cta=result.get("cta", "open_ended"),
        suppression_key=suppression_key,
        rationale=result.get("rationale", "")
    )
    
    actions.append(action)
    return TickResponse(actions=actions)


# ============================================================================
# ENDPOINT 3: POST /v1/reply
# ============================================================================

@app.post("/v1/reply")
async def reply(body: ReplyRequest):
    """
    Handle a merchant's (or customer's) reply to a message.
    
    1. Load conversation
    2. Parse intent (yes/no/wait/unclear)
    3. Check for auto-reply
    4. Decide next action (send/wait/end)
    5. Return synchronously
    
    Timeout: 30 seconds
    """
    
    # Load conversation
    conv = conv_manager.get(body.conversation_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "conversation not found"})
    
    # Add merchant's reply
    conv_manager.add_merchant_reply(
        body.conversation_id,
        body.message,
        body.received_at
    )
    
    # Recognize intent
    intent = recognize_intent(body.message)
    
    # Check for auto-reply
    recent_messages = [t.body for t in conv.turns if t.from_role == body.from_role]
    is_auto = is_auto_reply(recent_messages[-3:])  # Check last 3 messages
    
    # Decide action based on intent
    if is_auto:
        # Auto-reply detected: end after at most 1 turn
        return ReplyEndAction(
            action="end",
            rationale="Auto-reply detected; ending conversation to avoid wasted turns"
        ).dict()
    
    if intent == "affirm":
        # Merchant said yes - move to action mode
        conv_manager.set_state(body.conversation_id, "intent_action")
        return ReplySendAction(
            action="send",
            body="Great! I'll get that ready for you.",
            cta="open_ended",
            rationale="Affirmed intent; moving to action execution"
        ).dict()
    
    elif intent == "negate":
        # Merchant said no - end gracefully
        conv_manager.set_state(body.conversation_id, "ended")
        return ReplyEndAction(
            action="end",
            rationale="Merchant declined; respecting their preference"
        ).dict()
    
    elif intent == "wait":
        # Merchant asked for time
        conv_manager.set_waiting(body.conversation_id, wait_seconds=1800)  # 30 min
        return ReplyWaitAction(
            action="wait",
            wait_seconds=1800,
            rationale="Merchant requested time; backing off 30 minutes"
        ).dict()
    
    else:
        # Unclear intent - ask one clarifying question
        turn_count = len([t for t in conv.turns if t.from_role == "vera"])
        if turn_count >= 3:
            # Too many turns, end
            return ReplyEndAction(
                action="end",
                rationale="Maximum turns reached without clear intent; gracefully exiting"
            ).dict()
        
        # Ask a simple yes/no
        return ReplySendAction(
            action="send",
            body="Would you like to move forward with this?",
            cta="yes_no",
            rationale="Seeking clarification on merchant intent"
        ).dict()


# ============================================================================
# ENDPOINT 4: GET /v1/healthz
# ============================================================================

@app.get("/v1/healthz", response_model=HealthResponse)
async def healthz():
    """
    Liveness probe. Returns health status and context counts.
    
    Judge polls every 60 seconds.
    3 consecutive failures = disqualification.
    """
    uptime = int(time.time() - START_TIME)
    counts = store.get_counts()
    
    return HealthResponse(
        status="ok",
        uptime_seconds=uptime,
        contexts_loaded=counts
    )


# ============================================================================
# ENDPOINT 5: GET /v1/metadata
# ============================================================================

@app.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    """
    Bot identity and submission metadata.
    """
    return MetadataResponse(
        team_name=TEAM_NAME,
        team_members=TEAM_MEMBERS,
        model="claude-opus-4-7-20250219",
        approach="Deterministic trigger-based composer with template routing",
        contact_email=CONTACT_EMAIL,
        version=BOT_VERSION,
        submitted_at=SUBMITTED_AT
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": "Internal server error"}
    )


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load datasets and initialize on startup."""
    # In a real implementation, would load category data here
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Clear all state
    store.clear()


# ============================================================================
# TESTING ENDPOINT (for debugging)
# ============================================================================

@app.get("/debug/conversations")
async def debug_conversations():
    """Debug endpoint to view all conversations."""
    all_convs = conv_manager.all_conversations()
    return {
        "count": len(all_convs),
        "conversations": [
            {
                "id": c.conversation_id,
                "merchant": c.merchant_id,
                "state": c.state,
                "turns": len(c.turns)
            }
            for c in all_convs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
