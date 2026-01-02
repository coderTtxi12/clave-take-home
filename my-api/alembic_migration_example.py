"""Initial schema with PostgreSQL functions and triggers

Revision ID: initial_001
Revises: 
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'initial_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Leer y ejecutar los archivos SQL en orden
    # Nota: Necesitarías incluir todo el SQL aquí o leerlo de los archivos
    
    # Ejemplo: Ejecutar SQL directamente
    op.execute("""
        -- Contenido de 001_create_core_tables.sql
        -- Contenido de 002_create_order_items_and_payments.sql
        -- Contenido de 003_create_indexes.sql
        -- Contenido de 004_seed_reference_data.sql
    """)

def downgrade():
    # Eliminar todo
    op.execute("""
        DROP TABLE IF EXISTS toast_checks CASCADE;
        DROP TABLE IF EXISTS delivery_orders CASCADE;
        -- ... etc
    """)

