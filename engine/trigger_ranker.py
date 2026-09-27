"""
Trigger Ranking — score and select which trigger to act on.

Scoring factors:
- trigger_urgency (1-5)
- trigger type fit to merchant
- merchant performance context
- time sensitivity
- freshness
- suppression penalty (already sent this week)
- conversation state

Formula (example):
priority = urgency_weight
         + category_fit
         + merchant_fit
         + customer_fit
         + freshness_bonus
         + time_sensitivity
         - suppression_penalty
"""

from typing import Optional, Dict, Any, List, Tuple
from engine.context_store import get_store


def rank_triggers(trigger_ids: List[str], merchant_id: Optional[str] = None) -> List[Tuple[str, float]]:
    """
    Rank a list of triggers by priority.
    
    Returns:
        List of (trigger_id, score) tuples, sorted by score descending
    """
    store = get_store()
    scored = []
    
    for trigger_id in trigger_ids:
        trigger_ctx = store.get("trigger", trigger_id)
        if not trigger_ctx:
            continue
        
        payload = trigger_ctx.payload
        score = score_trigger(trigger_ctx.payload, merchant_id)
        scored.append((trigger_id, score))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def score_trigger(trigger_payload: Dict[str, Any], merchant_id: Optional[str] = None) -> float:
    """
    Score a single trigger.
    
    Returns:
        Numeric score (higher = more important)
    """
    score = 0.0
    
    # Base urgency (1-5)
    urgency = trigger_payload.get("urgency", 1)
    score += float(urgency) * 10  # 10-50 points
    
    # Trigger type bonus
    kind = trigger_payload.get("kind", "")
    if kind in ("perf_dip", "dormant_with_vera", "appointment_tomorrow", "customer_lapsed_soft"):
        score += 15  # High priority internal triggers
    elif kind in ("perf_spike", "milestone_reached", "review_theme_emerged"):
        score += 10  # Positive/engagement triggers
    elif kind in ("research_digest", "festival_upcoming", "trend_movement"):
        score += 8  # Knowledge/opportunity triggers
    elif kind in ("regulation_change", "weather_event", "competitor_opened"):
        score += 12  # External threats/compliance
    
    # Freshness bonus (if expires_at is in payload, newer = better)
    # This is simplified; in production might check against current time
    expires_at = trigger_payload.get("expires_at")
    if expires_at:
        # Recent expiry = more urgent
        score += 5
    
    # Scope (merchant vs customer)
    scope = trigger_payload.get("scope", "merchant")
    if scope == "merchant":
        score += 3  # Slightly prefer merchant outreach (usually higher success)
    
    return score


def select_top_trigger(trigger_ids: List[str], merchant_id: Optional[str] = None) -> Optional[str]:
    """
    Select the single highest-priority trigger from a list.
    
    Returns:
        The trigger_id with highest score, or None if list is empty
    """
    ranked = rank_triggers(trigger_ids, merchant_id)
    if ranked:
        return ranked[0][0]
    return None
