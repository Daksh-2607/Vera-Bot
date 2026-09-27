"""
Conversation State Machine — manages multi-turn conversations.

States:
- initiated: message sent, awaiting first reply
- awaiting_reply: awaiting reply after bot message
- intent_action: merchant said yes, ready to act
- waiting: merchant asked for time, in backoff
- ended: merchant said no or escalated to stop
- escalated: unclear/hostile, should stop
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    turn_number: int
    from_role: str  # "vera", "merchant", "customer"
    body: str
    received_at: str  # ISO 8601
    engagement_tag: Optional[str] = None


@dataclass
class ConversationState:
    """Full state of an active conversation."""
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    trigger_id: Optional[str] = None
    turns: List[ConversationTurn] = field(default_factory=list)
    state: str = "initiated"  # initiated, awaiting_reply, intent_action, waiting, ended, escalated
    suppression_keys_used: List[str] = field(default_factory=list)
    last_action_at: Optional[str] = None  # ISO 8601
    waiting_until: Optional[str] = None  # ISO 8601 (if in waiting state)
    
    def current_turn_number(self) -> int:
        """Get the next turn number."""
        return len(self.turns) + 1
    
    def add_turn(self, from_role: str, body: str, received_at: str, engagement_tag: Optional[str] = None):
        """Add a turn to the conversation."""
        turn = ConversationTurn(
            turn_number=self.current_turn_number(),
            from_role=from_role,
            body=body,
            received_at=received_at,
            engagement_tag=engagement_tag
        )
        self.turns.append(turn)
    
    def last_turn_body(self) -> Optional[str]:
        """Get the body of the last turn."""
        if self.turns:
            return self.turns[-1].body
        return None
    
    def vera_messages(self) -> List[str]:
        """Get all messages sent by Vera in this conversation."""
        return [t.body for t in self.turns if t.from_role == "vera"]
    
    def merchant_messages(self) -> List[str]:
        """Get all messages from the merchant."""
        return [t.body for t in self.turns if t.from_role == "merchant"]
    
    def has_repeated_message(self, body: str) -> bool:
        """Check if this exact body was already sent in this conversation."""
        return body in self.vera_messages()


class ConversationManager:
    """Manages all active conversations."""
    
    def __init__(self):
        # Key: conversation_id, Value: ConversationState
        self._conversations: Dict[str, ConversationState] = {}
        self._lock = threading.RLock()
    
    def create(self, conversation_id: str, merchant_id: str, customer_id: Optional[str] = None, trigger_id: Optional[str] = None) -> ConversationState:
        """Create a new conversation."""
        with self._lock:
            state = ConversationState(
                conversation_id=conversation_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                trigger_id=trigger_id,
                state="initiated"
            )
            self._conversations[conversation_id] = state
            return state
    
    def get(self, conversation_id: str) -> Optional[ConversationState]:
        """Get a conversation by ID."""
        with self._lock:
            return self._conversations.get(conversation_id)
    
    def add_vera_message(self, conversation_id: str, body: str, received_at: str):
        """Add a message sent by Vera."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv:
                conv.add_turn("vera", body, received_at)
    
    def add_merchant_reply(self, conversation_id: str, body: str, received_at: str, engagement_tag: Optional[str] = None):
        """Add a message from the merchant."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv:
                conv.add_turn("merchant", body, received_at, engagement_tag)
    
    def set_state(self, conversation_id: str, new_state: str):
        """Update conversation state."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv:
                conv.state = new_state
    
    def set_waiting(self, conversation_id: str, wait_seconds: int):
        """Set conversation to waiting state."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv:
                conv.state = "waiting"
                wait_until = datetime.utcnow() + timedelta(seconds=wait_seconds)
                conv.waiting_until = wait_until.isoformat() + "Z"
    
    def is_waiting_expired(self, conversation_id: str, now_iso: str) -> bool:
        """Check if a waiting conversation's wait period has expired."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv or conv.state != "waiting":
                return False
            if not conv.waiting_until:
                return False
            # Parse ISO strings and compare
            try:
                wait_until = datetime.fromisoformat(conv.waiting_until.rstrip('Z'))
                now = datetime.fromisoformat(now_iso.rstrip('Z'))
                return now >= wait_until
            except:
                return False
    
    def add_suppression_key(self, conversation_id: str, key: str):
        """Track a suppression key used in this conversation."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv and key not in conv.suppression_keys_used:
                conv.suppression_keys_used.append(key)
    
    def has_suppression_key(self, conversation_id: str, key: str) -> bool:
        """Check if a suppression key was already used."""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if conv:
                return key in conv.suppression_keys_used
            return False
    
    def all_conversations(self) -> List[ConversationState]:
        """Get all conversations."""
        with self._lock:
            return list(self._conversations.values())


# Global singleton
_manager = ConversationManager()


def get_manager() -> ConversationManager:
    """Get the global conversation manager."""
    return _manager
