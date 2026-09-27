"""
Context Store — maintains versioned context for all scope types.

Rules:
- Accept first version of any (scope, context_id)
- Accept newer version; replace older
- Reject stale versions (higher version exists)
- Never replace newer with older
- Make new context immediately available
"""

from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import threading


@dataclass
class StoredContext:
    """Internal representation of stored context."""
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: str
    stored_at: str


class ContextStore:
    """Thread-safe versioned context storage."""
    
    def __init__(self):
        # Key: (scope, context_id), Value: StoredContext
        self._contexts: Dict[Tuple[str, str], StoredContext] = {}
        self._lock = threading.RLock()
    
    def push(self, scope: str, context_id: str, version: int, payload: Dict[str, Any], delivered_at: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Push new or updated context.
        
        Returns:
            (accepted: bool, reason: str|None, current_version: int|None)
            - (True, None, None) if accepted
            - (False, "stale_version", current_version) if version is old
            - (False, "invalid_scope", None) if scope is invalid
        """
        if scope not in ("category", "merchant", "customer", "trigger"):
            return False, "invalid_scope", None
        
        key = (scope, context_id)
        now_iso = datetime.utcnow().isoformat() + "Z"
        
        with self._lock:
            existing = self._contexts.get(key)
            if existing and existing.version >= version:
                # Stale version — reject
                return False, "stale_version", existing.version
            
            # Accept and store
            stored = StoredContext(
                scope=scope,
                context_id=context_id,
                version=version,
                payload=payload,
                delivered_at=delivered_at,
                stored_at=now_iso
            )
            self._contexts[key] = stored
            return True, None, None
    
    def get(self, scope: str, context_id: str) -> Optional[StoredContext]:
        """Retrieve current context by scope and context_id."""
        with self._lock:
            return self._contexts.get((scope, context_id))
    
    def get_by_scope(self, scope: str) -> Dict[str, StoredContext]:
        """Get all contexts of a given scope."""
        with self._lock:
            return {
                cid: ctx
                for (s, cid), ctx in self._contexts.items()
                if s == scope
            }
    
    def get_counts(self) -> Dict[str, int]:
        """Get count of contexts by scope."""
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        with self._lock:
            for (scope, _), _ in self._contexts.items():
                counts[scope] = counts.get(scope, 0) + 1
        return counts
    
    def clear(self):
        """Clear all contexts (for testing or teardown)."""
        with self._lock:
            self._contexts.clear()


# Global singleton
_store = ContextStore()


def get_store() -> ContextStore:
    """Get the global context store."""
    return _store
