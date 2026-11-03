"""Snapshots de documentos e rastreabilidade de entrega, preservando documentos antigos."""
from alembic import op
import sqlalchemy as sa

revision="20261012_nexo_documents"
down_revision="20261012_fiscal_central"
branch_labels=None
depends_on=None


def upgrade():
    with op.batch_alter_table("notas_fiscais") as batch:
        batch.add_column(sa.Column("document_snapshot",sa.JSON(),nullable=True))
        batch.add_column(sa.Column("document_pdf",sa.LargeBinary(),nullable=True))
        batch.add_column(sa.Column("document_xml",sa.Text(),nullable=True))
    op.create_table("entregas_email",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("academy_id",sa.Integer(),sa.ForeignKey("academias.id"),nullable=False),
        sa.Column("invoice_id",sa.Integer(),sa.ForeignKey("notas_fiscais.id"),nullable=False),
        sa.Column("user_id",sa.Integer(),sa.ForeignKey("usuarios.id"),nullable=False),
        sa.Column("recipient",sa.String(254),nullable=False),
        sa.Column("subject",sa.String(200),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("idempotency_key",sa.String(100),nullable=False,unique=True),
        sa.Column("message",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_entregas_email_academy_id","entregas_email",["academy_id"])
    op.create_index("ix_entregas_email_invoice_id","entregas_email",["invoice_id"])


def downgrade():
    if not op.get_context().as_sql and op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM entregas_email")):
        raise RuntimeError("Downgrade bloqueado: preserve o histórico de entrega.")
    op.drop_table("entregas_email")
    with op.batch_alter_table("notas_fiscais") as batch:
        batch.drop_column("document_xml")
        batch.drop_column("document_pdf")
        batch.drop_column("document_snapshot")
