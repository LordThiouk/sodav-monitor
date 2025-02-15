"""fix report status

Revision ID: fix_report_status
Revises: 94c2b5cec5f0
Create Date: 2025-02-09 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_report_status'
down_revision = '94c2b5cec5f0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop the existing table
    op.drop_table('reports')
    
    # Create new table with string status
    op.create_table('reports',
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
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    # Drop the new table
    op.drop_table('reports')
    
    # Recreate original table with enum status
    op.create_table('reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), server_default='csv', nullable=False),
        sa.Column('status', sa.Enum('pending', 'generating', 'completed', 'failed', name='reportstatus'), server_default='pending', nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    ) 