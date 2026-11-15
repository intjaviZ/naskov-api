"""merge_heads

Revision ID: ee210007f397
Revises: 3a4a50294999, 748be30b72d0
Create Date: 2026-11-15 03:41:29.525742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee210007f397'
down_revision: Union[str, Sequence[str], None] = ('3a4a50294999', '748be30b72d0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
