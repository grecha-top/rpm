"""Shared Pact V4 definition for the OrderPaid asynchronous message."""
from pact import Pact
from pact import match


DESCRIPTION = "an OrderPaid event"


def build_order_paid_pact() -> Pact:
    pact = Pact("Sirius Kitchen", "Sirius Orders").with_specification("V4")
    pact.upon_receiving(DESCRIPTION, "Async").with_body(
        {
            "event_id": match.uuid("00000000-0000-4000-8000-000000000001"),
            "event_type": "OrderPaid",
            "event_version": match.integer(1),
            "occurred_at": match.string("2026-11-24T12:00:00+00:00"),
            "correlation_id": match.string("pact-correlation-42"),
            "payload": {
                "order_id": match.integer(1),
                "customer_id": match.integer(7),
                "amount": match.number(300.0),
                "total": match.number(300.0),
                "currency": "RUB",
            },
        },
        "application/json",
    )
    return pact
