import json
from pathlib import Path
from types import SimpleNamespace

from pact import Verifier

from app.modules.orders.service import OrderService
from tests.contract.order_paid_pact import DESCRIPTION, build_order_paid_pact


PACT_PATH = Path(__file__).parent / "pacts" / "Sirius Kitchen-Sirius Orders.json"


class ContractRepository:
    def __init__(self):
        self.order = SimpleNamespace(id=42, user_id=7, total=300.0, status="processing")
        self.event = None

    def get_order(self, order_id):
        return self.order if order_id == self.order.id else None

    def pay_order(self, order, user, new_balance, event):
        self.event = event
        order.status = "paid"
        user.balance = new_balance


def test_kitchen_consumer_accepts_order_paid_message():
    consumed = []

    def consume(body, _metadata):
        event = json.loads(body)
        assert event["event_type"] == "OrderPaid"
        assert event["payload"]["order_id"] > 0
        assert event["payload"]["total"] > 0
        assert event["payload"]["currency"] == "RUB"
        consumed.append(event)

    build_order_paid_pact().verify(consume, "Async")
    assert len(consumed) == 1


def produce_order_paid_message():
    repository = ContractRepository()
    user = SimpleNamespace(id=7, balance=1000.0)
    OrderService(repository).pay_order(42, user, correlation_id="pact-42")
    return {
        "contents": json.dumps(repository.event).encode("utf-8"),
        "content_type": "application/json",
        "metadata": {},
    }


def test_orders_provider_satisfies_generated_kitchen_pact():
    assert PACT_PATH.exists(), "Run python scripts/generate_order_paid_pact.py"
    (
        Verifier("Sirius Orders")
        .add_source(PACT_PATH)
        .message_handler({DESCRIPTION: produce_order_paid_message})
        .verify()
    )
