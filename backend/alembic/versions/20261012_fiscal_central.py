"""Emissão avulsa e origem das notas; preserva notas vinculadas a cobranças."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_fiscal_central"
down_revision = "06fd40e34ab2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("alunos") as batch:
        batch.alter_column("cpf",existing_type=sa.String(11),nullable=True)
        batch.add_column(sa.Column("person_type",sa.String(2),nullable=False,server_default="pf"))
        batch.add_column(sa.Column("cnpj",sa.String(14),nullable=True))
        batch.add_column(sa.Column("trade_name",sa.String(120),nullable=False,server_default=""))
        batch.add_column(sa.Column("municipal_registration",sa.String(50),nullable=False,server_default=""))
        batch.create_unique_constraint("uq_clientes_cnpj",["academy_id","cnpj"])
        batch.create_check_constraint("ck_clientes_documento","(person_type = 'pf' AND cpf IS NOT NULL AND cnpj IS NULL) OR (person_type = 'pj' AND cnpj IS NOT NULL AND cpf IS NULL)")
    with op.batch_alter_table("notas_fiscais") as batch:
        batch.alter_column("charge_id", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("service_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("origin", sa.String(20), nullable=False, server_default="cobranca"))
        batch.add_column(sa.Column("competence", sa.String(7), nullable=True))
        batch.add_column(sa.Column("request_hash", sa.String(64), nullable=True))
        batch.create_foreign_key("fk_notas_servico", "servicos", ["service_id"], ["id"])
        batch.create_check_constraint("ck_notas_origem", "(origin = 'cobranca' AND charge_id IS NOT NULL) OR (origin = 'avulsa' AND charge_id IS NULL AND service_id IS NOT NULL)")


def downgrade():
    if not op.get_context().as_sql:
        count = op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM notas_fiscais WHERE charge_id IS NULL"))
        if count:
            raise RuntimeError("Downgrade bloqueado: existem notas avulsas. Preserve o histórico fiscal.")
        if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM alunos WHERE person_type='pj'")):
            raise RuntimeError("Downgrade bloqueado: existem clientes pessoa jurídica. Preserve os cadastros.")
    with op.batch_alter_table("notas_fiscais") as batch:
        batch.drop_constraint("ck_notas_origem", type_="check")
        batch.drop_constraint("fk_notas_servico", type_="foreignkey")
        for name in ("request_hash", "competence", "origin", "service_id"):
            batch.drop_column(name)
        batch.alter_column("charge_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("alunos") as batch:
        batch.drop_constraint("ck_clientes_documento",type_="check")
        batch.drop_constraint("uq_clientes_cnpj",type_="unique")
        for name in ("municipal_registration","trade_name","cnpj","person_type"):
            batch.drop_column(name)
        batch.alter_column("cpf",existing_type=sa.String(11),nullable=False)
