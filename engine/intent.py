"""
Intent Recognition — parse merchant replies for intent.

Intent types:
- AFFIRM: yes, sure, go ahead, do it, kar do, haan, ok, okau
- NEGATE: no, nope, not interested, stop, don't contact, remove me
- WAIT: later, tomorrow, ask after, busy, call later
- UNCLEAR: anything else
"""

import re
from typing import Literal


IntentType = Literal["affirm", "negate", "wait", "unclear"]


# Patterns for different languages (English, Hindi, hi-en mix)

AFFIRM_PATTERNS = [
    r'\byes?\b',
    r'\bsure\b',
    r'\bgood\b',
    r'\bgo ahead\b',
    r'\bgo for it\b',
    r'\bdo it\b',
    r'\bsend it\b',
    r'\bokay\b',
    r'\bokau\b',
    r'\bkarao\b',
    r'\bkar do\b',
    r'\bhaan\b',
    r'\bji\b',
    r'\babsolutely\b',
    r'\bcertainly\b',
    r'\bdone\b',
    r'\bproceed\b',
    r'\blet\'s do it\b',
    r'\bdefintely\b',
]

NEGATE_PATTERNS = [
    r'\bno\b',
    r'\bnope\b',
    r'\bnot interested\b',
    r'\bdont\b',
    r'\bdon\'t\b',
    r'\bstop\b',
    r'\bremove\b',
    r'\bstop messaging\b',
    r'\bno thanks\b',
    r'\bnot now\b',
    r'\bgo away\b',
    r'\bleave me\b',
    r'\bnahi\b',
    r'\bmatlab\b',
    r'\bkuch nahi\b',
    r'\bnot interested\b',
    r'\bdont contact\b',
]

WAIT_PATTERNS = [
    r'\blater\b',
    r'\btomorrow\b',
    r'\bbusy\b',
    r'\bask me\s+(?:later|tomorrow|after)',
    r'\bcall me\s+(?:later|tomorrow)',
    r'\bafter some time\b',
    r'\bbaad mein\b',
    r'\bkaal\b',
    r'\bfree nahi\b',
]


def recognize_intent(message: str) -> IntentType:
    """
    Parse a merchant's message and extract intent.
    
    Args:
        message: The merchant's reply text
    
    Returns:
        One of: "affirm", "negate", "wait", "unclear"
    """
    if not message or not isinstance(message, str):
        return "unclear"
    
    # Normalize: lowercase, strip whitespace
    msg = message.lower().strip()
    
    # Check patterns in order of priority
    for pattern in AFFIRM_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return "affirm"
    
    for pattern in NEGATE_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return "negate"
    
    for pattern in WAIT_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return "wait"
    
    return "unclear"


def is_auto_reply(messages: list[str], threshold: int = 3) -> bool:
    """
    Detect if the messages are likely automated replies.
    
    Auto-replies typically:
    - Same message verbatim 3+ times
    - Common auto-reply phrases
    
    Args:
        messages: List of message bodies
        threshold: Number of identical messages to flag as auto-reply
    
    Returns:
        True if likely auto-reply, False otherwise
    """
    if len(messages) < threshold:
        return False
    
    # Check for exact duplicate messages
    from collections import Counter
    counts = Counter(messages)
    if any(count >= threshold for count in counts.values()):
        return True
    
    # Check for common auto-reply phrases
    auto_reply_phrases = [
        "thank you for contacting",
        "thank you for messaging",
        "our team will get back",
        "will respond shortly",
        "automated response",
        "auto reply",
        "away",
        "out of office",
        "unable to respond",
        "message received",
    ]
    
    # Check if recent messages (last 2-3) contain auto-reply markers
    recent = messages[-2:] if len(messages) >= 2 else messages
    for msg in recent:
        msg_lower = msg.lower()
        for phrase in auto_reply_phrases:
            if phrase in msg_lower:
                return True
    
    return False
