"""Builders for the event envelopes exchanged through RabbitMQ."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


def build_event(
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> dict:
    return {
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id or str(uuid4()),
        "payload": payload,
    }
