"""Prepare deterministic, repeatable data for the labs 5-8 demonstration."""
import json

from redis import RedisError

from app.core.redis import redis_client
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import (
    Delivery,
    KitchenOrder,
    MenuItem,
    Order,
    OutboxEvent,
    ProcessedEvent,
    RefreshToken,
    Role,
    User,
)


PASSWORD = "demo-password"
ADMIN_EMAIL = "demo.admin@example.com"
COURIER_EMAIL = "demo.courier@example.com"
RESERVATION_EMAIL = "demo.reservation@example.com"
LEGACY_EMAILS = {
    ADMIN_EMAIL: "demo.admin@sirius.local",
    COURIER_EMAIL: "demo.courier@sirius.local",
    RESERVATION_EMAIL: "demo.reservation@sirius.local",
}
MENU_ITEMS = (
    ("Демо сырники с малиной", 250.0),
    ("Демо чай с облепихой", 120.0),
)


def upsert_user(db, email: str, role: Role, balance: float) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, phone="+79990000000")
    user.password_hash = hash_password(PASSWORD)
    user.role_id = role.id
    user.balance = balance
    user.is_blocked = False
    db.add(user)
    db.flush()
    return user


def migrate_legacy_users(db) -> None:
    """Keep demo rows made by an older script, but use valid public domains."""
    for current_email, legacy_email in LEGACY_EMAILS.items():
        current = db.query(User).filter(User.email == current_email).first()
        legacy = db.query(User).filter(User.email == legacy_email).first()
        if legacy and not current:
            legacy.email = current_email
    db.flush()


def event_order_id(event: OutboxEvent):
    try:
        return event.payload["payload"]["order_id"]
    except (KeyError, TypeError):
        return None


def clean_previous_demo(db, admin: User, courier: User, reservation: User) -> None:
    demo_orders = (
        db.query(Order)
        .filter(Order.user_id.in_((admin.id, reservation.id)))
        .all()
    )
    order_ids = [order.id for order in demo_orders]

    # The demo courier belongs exclusively to this script, so resetting their
    # previous assignment cannot affect a real user.
    db.query(Delivery).filter(Delivery.courier_id == courier.id).delete(
        synchronize_session=False
    )
    if order_ids:
        db.query(Delivery).filter(Delivery.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.query(KitchenOrder).filter(KitchenOrder.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )

        related_events = [
            event
            for event in db.query(OutboxEvent).all()
            if event_order_id(event) in order_ids
        ]
        event_ids = [event.id for event in related_events]
        if event_ids:
            db.query(ProcessedEvent).filter(
                ProcessedEvent.event_id.in_(event_ids)
            ).delete(synchronize_session=False)
            for event in related_events:
                db.delete(event)

        db.query(Order).filter(Order.id.in_(order_ids)).delete(
            synchronize_session=False
        )

    db.query(RefreshToken).filter(
        RefreshToken.user_id.in_((admin.id, courier.id, reservation.id))
    ).delete(synchronize_session=False)
    db.flush()

    try:
        for order_id in order_ids:
            keys = []
            for effect in ("pdf", "email", "sms"):
                keys.extend(
                    (
                        f"order:{order_id}:{effect}:completed",
                        f"order:{order_id}:{effect}:lock",
                    )
                )
            redis_client.delete(*keys)
    except RedisError:
        pass


def prepare():
    db = SessionLocal()
    try:
        roles = {role.name: role for role in db.query(Role).all()}
        missing = {"admin", "courier", "student"} - roles.keys()
        if missing:
            raise RuntimeError(f"Missing roles: {', '.join(sorted(missing))}")

        migrate_legacy_users(db)
        admin = upsert_user(db, ADMIN_EMAIL, roles["admin"], 10000.0)
        courier = upsert_user(db, COURIER_EMAIL, roles["courier"], 0.0)
        reservation = upsert_user(db, RESERVATION_EMAIL, roles["student"], 0.0)
        clean_previous_demo(db, admin, courier, reservation)

        menu = []
        for name, price in MENU_ITEMS:
            item = db.query(MenuItem).filter(MenuItem.name == name).first()
            if not item:
                item = MenuItem(name=name)
            item.price = price
            item.is_available = True
            db.add(item)
            db.flush()
            menu.append(item)

        # Reserve every non-demo courier who is currently free. This leaves
        # exactly one free demo courier: the first paid order gets assigned to
        # them, while the second one reliably exercises the Saga compensation.
        reserved_couriers = []
        other_couriers = (
            db.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "courier", User.id != courier.id, User.is_blocked.is_(False))
            .all()
        )
        for other in other_couriers:
            active = (
                db.query(Delivery)
                .filter(
                    Delivery.courier_id == other.id,
                    Delivery.status.in_(("in_progress", "on_the_way")),
                )
                .first()
            )
            if active:
                continue
            order = Order(
                user_id=reservation.id,
                item_id=menu[0].id,
                quantity=1,
                total=0.0,
                status="paid",
            )
            db.add(order)
            db.flush()
            db.add(
                Delivery(
                    order_id=order.id,
                    courier_id=other.id,
                    status="in_progress",
                )
            )
            reserved_couriers.append(other.email)

        db.commit()
        try:
            redis_client.delete("menu:all")
        except RedisError:
            pass

        print(
            json.dumps(
                {
                    "password": PASSWORD,
                    "admin": {"id": admin.id, "email": ADMIN_EMAIL, "balance": 10000},
                    "courier": {"id": courier.id, "email": COURIER_EMAIL},
                    "menu": [{"id": item.id, "name": item.name, "price": item.price} for item in menu],
                    "reserved_non_demo_couriers": reserved_couriers,
                    "next": "Follow DEMO_GUIDE.md",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    prepare()
