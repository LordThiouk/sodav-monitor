"""add reports tables

Revision ID: add_reports_tables
Revises: merge_heads
Create Date: 2024-02-09 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_reports_tables'
down_revision = 'merge_heads'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), server_default='csv', nullable=False),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'generating', 'completed', 'failed')")
    )

    # Create report_subscriptions table
    op.create_table(
        'report_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('recipients', sa.JSON(), nullable=False),
        sa.Column('next_delivery', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_sent', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_reports_created_at'), 'reports', ['created_at'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_report_subscriptions_next_delivery'), 'report_subscriptions', ['next_delivery'], unique=False)
    op.create_index(op.f('ix_report_subscriptions_is_active'), 'report_subscriptions', ['is_active'], unique=False)

def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_report_subscriptions_is_active'), table_name='report_subscriptions')
    op.drop_index(op.f('ix_report_subscriptions_next_delivery'), table_name='report_subscriptions')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_created_at'), table_name='reports')

    # Drop tables
    op.drop_table('report_subscriptions')
    op.drop_table('reports') 