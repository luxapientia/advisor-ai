"""Initial migration from existing tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-09-27 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Note: All tables already exist from previous auto-creation
    # This migration serves as a baseline for future changes
    pass


def downgrade() -> None:
    # Note: We don't drop tables in downgrade to preserve data
    # Individual migrations should handle their own rollbacks
    pass