"""Adiciona demonstração genérica; preserva notas e contratos históricos existentes."""
from decimal import Decimal
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.entities import Academy, Student, Service


def provision():
    with SessionLocal() as db:
        company=db.scalar(select(Academy).order_by(Academy.id))
        if not company:
            raise SystemExit("Aplique o seed antes de preparar a demonstração genérica.")
        if company.name=="Academia Movimento" and company.cnpj=="00000000000191":
            company.name="Horizonte Serviços • Demonstração"
            company.legal_name="Horizonte Serviços Ltda. (fictícia)"
        catalog=[("Consultoria","350.00"),("Prestação de serviços","180.00"),("Suporte técnico","120.00"),("Treinamento","250.00"),("Desenvolvimento de projeto","900.00")]
        for name,price in catalog:
            exists=db.scalar(select(Service).where(Service.academy_id==company.id,Service.name==name))
            if not exists:
                db.add(Service(academy_id=company.id,name=name,price=Decimal(price),unit="serviço",description="Serviço fictício para demonstração do emissor"))
        legacy_names={"Avaliação física","Personal trainer","Aula experimental","Treino individual","Consultoria esportiva"}
        for service in db.scalars(select(Service).where(Service.academy_id==company.id)).all():
            if service.name in legacy_names and service.description=="Serviço demonstrativo":
                service.status="inativo"
        if not db.scalar(select(Student).where(Student.academy_id==company.id,Student.cnpj=="11222333000181")):
            db.add(Student(academy_id=company.id,person_type="pj",name="Empresa Beta • Cliente fictício",trade_name="Beta Demonstração",cnpj="11222333000181",email="empresa-beta@nexofiscal.example.com",address={"city":"São Paulo","state":"SP"},notes="Cliente pessoa jurídica fictício para portfólio."))
        db.commit()
    print("Demonstração genérica preparada. Histórico fiscal preservado.")


if __name__=="__main__":
    provision()
