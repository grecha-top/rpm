def test_create_order_saves_to_real_postgres(scenario, db):
    from app.models import Order

    response = scenario.client.post(
        "/orders/create",
        headers={"X-Correlation-ID": "integration-create-42"},
        json={"item_id": scenario.item.id, "quantity": 2},
    )

    assert response.status_code == 201
    assert response.headers["X-Correlation-ID"] == "integration-create-42"
    order = db.get(Order, response.json()["order_id"])
    assert order is not None
    assert order.quantity == 2
    assert order.total == 300.0


def test_payment_outbox_preserves_correlation_and_contract(scenario, db):
    from app.models import OutboxEvent

    created = scenario.client.post(
        "/orders/create",
        json={"item_id": scenario.item.id, "quantity": 1},
    )
    order_id = created.json()["order_id"]

    paid = scenario.client.post(
        f"/orders/{order_id}/pay",
        headers={"X-Correlation-ID": "integration-pay-42"},
    )

    assert paid.status_code == 200
    event = db.query(OutboxEvent).filter_by(event_type="OrderPaid").one()
    assert event.payload["correlation_id"] == "integration-pay-42"
    assert event.payload["payload"] == {
        "order_id": order_id,
        "customer_id": scenario.user.id,
        "amount": 150.0,
        "total": 150.0,
        "currency": "RUB",
    }
