"""add persisted order total

Revision ID: 0002_order_total
Revises: 0001_security_and_menu
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_order_total"
down_revision = "0001_security_and_menu"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "orders",
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
    )
    op.alter_column("orders", "total", server_default=None)


def downgrade():
    op.drop_column("orders", "total")
