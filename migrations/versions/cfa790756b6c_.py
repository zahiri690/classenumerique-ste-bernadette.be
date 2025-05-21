"""empty message

Revision ID: cfa790756b6c
Revises: 42f1aa1efe44, add_max_attempts_column, c47e2439a355
Create Date: 2025-05-09 23:29:07.331626

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cfa790756b6c'
down_revision = ('42f1aa1efe44', 'add_max_attempts_column', 'c47e2439a355')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
