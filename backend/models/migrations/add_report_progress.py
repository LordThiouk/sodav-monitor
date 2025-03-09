"""Add progress column to reports table

This migration adds a progress column to track report generation progress.
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add progress column
    op.add_column('reports', sa.Column('progress', sa.Float, nullable=False, server_default='0.0'))
    
    # Update existing reports
    op.execute("""
        UPDATE reports 
        SET progress = CASE 
            WHEN status = 'completed' THEN 1.0 
            WHEN status = 'failed' THEN 0.0 
            ELSE 0.0 
        END
    """)

def downgrade():
    # Remove progress column
    op.drop_column('reports', 'progress') 