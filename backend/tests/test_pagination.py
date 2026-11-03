from decimal import Decimal
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.entities import Academy, Audit, Automation, AutomationRun, Service, User


def test_automation_history_pages_filter_and_company_scope(authenticated):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == 'administrador'))
        workflow = Automation(academy_id=user.academy_id, name='Alertas', workflow_key='alerts', implemented=True)
        other = Academy(name='Outra empresa', legal_name='Outra Ltda', cnpj='11111111000111')
        db.add_all([workflow, other]); db.flush()
        foreign = Automation(academy_id=other.id, name='Externa', workflow_key='foreign-alerts')
        db.add(foreign); db.flush()
        for index in range(25):
            db.add(AutomationRun(automation_id=workflow.id, status='sucesso' if index % 2 == 0 else 'erro', source='local', message=f'Execução {index}'))
        db.add(AutomationRun(automation_id=foreign.id, status='sucesso', message='Registro de outra empresa'))
        db.commit()
    pages = [authenticated.get(f'/api/automations?page={page}').json() for page in (1, 2, 3, 4, 5)]
    assert [len(page['runs']) for page in pages] == [5, 5, 5, 5, 5]
    assert all(page['runs_total'] == page['runs_count'] == 25 and page['page_size'] == 5 for page in pages)
    identities = [row['id'] for page in pages for row in page['runs']]
    assert len(set(identities)) == 25
    assert identities == sorted(identities, reverse=True)
    assert all('outra empresa' not in row['message'] for page in pages for row in page['runs'])
    filtered = [authenticated.get(f'/api/automations?page={page}&status=erro').json() for page in (1, 2, 3)]
    assert [len(page['runs']) for page in filtered] == [5, 5, 2]
    assert all(page['runs_total'] == 12 and page['runs_count'] == 25 for page in filtered)
    assert all(row['status'] == 'erro' for page in filtered for row in page['runs'])
    assert authenticated.get('/api/automations?page=0').status_code == 422
    assert authenticated.get('/api/automations?status=invalid').status_code == 422


def test_audit_uses_five_items_and_does_not_repeat(authenticated):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == 'administrador'))
        for index in range(24):
            db.add(Audit(academy_id=user.academy_id, user_id=user.id, action='verificar_paginacao', entity='teste', entity_id=index))
        db.commit()
    first = authenticated.get('/api/audit').json()
    pages = [first] + [authenticated.get(f'/api/audit?page={page}').json() for page in range(2, (first['total'] + 4) // 5 + 1)]
    assert [len(page['items']) for page in pages] == [5, 5, 5, 5, 5]
    assert all(page['page_size'] == 5 for page in pages)
    assert len({row['id'] for page in pages for row in page['items']}) == first['total']


def test_search_can_reach_matches_after_old_preview_limit(authenticated):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.role == 'administrador'))
        other = Academy(name='Outra', legal_name='Outra Ltda', cnpj='22222222000122')
        db.add(other); db.flush()
        for index in range(25):
            db.add(Service(academy_id=user.academy_id, name=f'Busca Paginada {index:02}', price=Decimal('10')))
        db.add(Service(academy_id=other.id, name='Busca Paginada externa', price=Decimal('10')))
        db.commit()
    pages = [authenticated.get(f'/api/search?q=Busca%20Paginada&paginate=true&page={page}').json() for page in (1, 2, 3, 4, 5)]
    assert [len(page['items']) for page in pages] == [5, 5, 5, 5, 5]
    assert all(page['total'] == 25 for page in pages)
    rows = [row for page in pages for row in page['items']]
    assert len({(row['resource'], row['id']) for row in rows}) == 25
    assert not any('externa' in row['title'] for row in rows)
    assert isinstance(authenticated.get('/api/search?q=Busca%20Paginada').json(), list)
    assert authenticated.get('/api/search?q=x&paginate=true').json()['items'] == []
