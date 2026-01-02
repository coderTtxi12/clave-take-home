"""add_unknown_to_payment_type_enum

Revision ID: add_unknown_payment
Revises: 8acb2927bf44
Create Date: 2025-01-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_unknown_payment'
down_revision: Union[str, None] = '8acb2927bf44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UNKNOWN to paymenttypeenum."""
    # Add 'UNKNOWN' value to the existing paymenttypeenum
    op.execute("ALTER TYPE paymenttypeenum ADD VALUE IF NOT EXISTS 'UNKNOWN'")


def downgrade() -> None:
    """Remove UNKNOWN from paymenttypeenum."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum, which is complex
    # For now, we'll leave UNKNOWN in place even on downgrade
    # If you need to truly remove it, you'd need to:
    # 1. Create a new enum without UNKNOWN
    # 2. Update all columns to use the new enum
    # 3. Drop the old enum
    # 4. Rename the new enum
    pass

