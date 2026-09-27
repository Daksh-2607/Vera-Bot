"""
Consent Checking — enforce customer communication consent.

Rules:
- Customer outreach requires explicit consent
- Check consent.scope for the intended action
- Allowed scopes: recall_reminders, appointment_reminders, promotional_offers, ...
- If scope is empty or absent → do not send
"""

from typing import Optional, Dict, Any, List


def has_consent(customer_context: Optional[Dict[str, Any]], action_type: str) -> bool:
    """
    Check if a customer has consented to an action type.
    
    Args:
        customer_context: The customer context from the judge
        action_type: What we want to send (e.g., "recall_reminders", "appointment_reminders")
    
    Returns:
        True if consent exists and covers the action, False otherwise
    """
    if not customer_context:
        # No customer context = no consent
        return False
    
    consent = customer_context.get("consent")
    if not consent:
        return False
    
    scope = consent.get("scope", [])
    if not scope or not isinstance(scope, list):
        return False
    
    # Check if action_type is in the consent scope
    return action_type in scope


def get_consented_scopes(customer_context: Optional[Dict[str, Any]]) -> List[str]:
    """
    Get all consented communication scopes for a customer.
    
    Args:
        customer_context: The customer context from the judge
    
    Returns:
        List of consented scopes, or empty list if no consent
    """
    if not customer_context:
        return []
    
    consent = customer_context.get("consent")
    if not consent:
        return []
    
    scope = consent.get("scope", [])
    if not isinstance(scope, list):
        return []
    
    return scope
