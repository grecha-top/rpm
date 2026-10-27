"""add event-driven architecture tables

Revision ID: 0003_event_architecture
Revises: 0002_order_total
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_event_architecture"
down_revision = "0002_order_total"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kitchen_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
    )
    op.create_table(
        "processed_events",
        sa.Column("consumer_name", sa.String(100), primary_key=True),
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("routing_key", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table("outbox_events")
    op.drop_table("processed_events")
    op.drop_table("kitchen_orders")
