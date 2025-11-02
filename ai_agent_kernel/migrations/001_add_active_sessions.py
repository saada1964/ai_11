"""
Add ActiveSession table for session management

Revision ID: 001_add_active_sessions
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '001_add_active_sessions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add ActiveSession table"""
    op.create_table(
        'active_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=False),
        sa.Column('device_info', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_active_sessions_id', 'active_sessions', ['id'])
    op.create_index('ix_active_sessions_session_token', 'active_sessions', ['session_token'], unique=True)
    op.create_index('ix_active_sessions_refresh_token', 'active_sessions', ['refresh_token'], unique=True)
    op.create_index('ix_active_sessions_user_id', 'active_sessions', ['user_id'])
    op.create_index('ix_active_sessions_is_active', 'active_sessions', ['is_active'])
    op.create_index('ix_active_sessions_expires_at', 'active_sessions', ['expires_at'])


def downgrade():
    """Remove ActiveSession table"""
    op.drop_table('active_sessions')