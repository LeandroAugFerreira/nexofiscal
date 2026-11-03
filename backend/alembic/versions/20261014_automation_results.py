"""Resultados das rotinas locais/n8n, sem ativar execuções automaticamente."""
from alembic import op
import sqlalchemy as sa

revision = '20261014_automation_results'
down_revision = '20261012_nexo_documents'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('execucoes_automacoes', sa.Column('source', sa.String(20), nullable=False, server_default='n8n'))
    op.add_column('execucoes_automacoes', sa.Column('result_data', sa.JSON(), nullable=True))
    op.add_column('execucoes_automacoes', sa.Column('idempotency_key', sa.String(100), nullable=True))
    op.add_column('execucoes_automacoes', sa.Column('request_hash', sa.String(64), nullable=True))
    op.create_index('ix_execucoes_automacoes_idempotency_key', 'execucoes_automacoes', ['idempotency_key'], unique=True)
    keys = ['payment-confirmed', 'document-delivery', 'due-reminders', 'failure-recovery', 'monthly-closing', 'alerts']
    for key in keys:
        op.execute(sa.text('UPDATE automacoes SET implemented = :implemented WHERE workflow_key = :key').bindparams(implemented=True, key=key))


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT COUNT(*) FROM execucoes_automacoes WHERE result_data IS NOT NULL')):
        raise RuntimeError('Preserve o histórico de resultados das automações antes de reverter.')
    op.drop_index('ix_execucoes_automacoes_idempotency_key', table_name='execucoes_automacoes')
    with op.batch_alter_table('execucoes_automacoes') as batch:
        for name in ('request_hash', 'idempotency_key', 'result_data', 'source'):
            batch.drop_column(name)
    op.execute("UPDATE automacoes SET implemented = false WHERE workflow_key <> 'payment-confirmed'")
