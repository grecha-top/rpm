"""add security fields and menu categories

Revision ID: 0001_security_and_menu
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_security_and_menu"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_role", "users", "roles", ["role_id"], ["id"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.add_column("menu_items", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_menu_items_category", "menu_items", "menu_categories", ["category_id"], ["id"]
    )
    op.execute(
        "INSERT INTO roles (name) VALUES ('student'), ('cook'), ('courier'), ('admin')"
    )
    op.execute(
        "UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'student')"
    )


def downgrade():
    op.drop_constraint("fk_menu_items_category", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "category_id")
    op.drop_table("menu_categories")
    op.drop_table("refresh_tokens")
    op.drop_constraint("fk_users_role", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_column("users", "password_hash")
    op.drop_table("roles")
