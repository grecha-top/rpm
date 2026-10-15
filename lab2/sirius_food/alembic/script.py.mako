"""${message}"""
from alembic import op
import sqlalchemy as sa

revision = '${up_revision}'
down_revision = '${down_revision}'
branch_labels = ${branch_labels}
depends_on = ${depends_on}


def upgrade():
    ${upgrades if upgrades else 'pass'}


def downgrade():
    ${downgrades if downgrades else 'pass'}
