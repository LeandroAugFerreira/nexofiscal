from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import AuthSession, User
from app.repositories.records import audit, serialize
from app.schemas.accounts import UserCreate, UserUpdate
from app.security.auth import current_user, hasher

router = APIRouter(prefix="/users", tags=["Contas"])


def administrator(user=Depends(current_user)):
    # A conta pública possui acesso de consulta à tela, mas não pode criar
    # contas privilegiadas nem alterar credenciais de outros usuários.
    if user.role != "administrador":
        raise HTTPException(403, "Somente o Administrador pode gerenciar contas.")
    return user


def available_email(db, email, identity=None):
    existing = db.scalar(select(User).where(User.email == email))
    if existing and existing.id != identity:
        raise HTTPException(409, "Este e-mail já está em uso. Escolha outro endereço.")


@router.post("", status_code=201)
def create_account(data: UserCreate, user=Depends(administrator), db: Session = Depends(get_db)):
    available_email(db, str(data.email))
    row = User(academy_id=user.academy_id, name=data.name, email=str(data.email),
        role=data.role, active=data.active, password_hash=hasher.hash(data.password.get_secret_value()))
    db.add(row)
    db.flush()
    audit(db, user, "criar_usuario", "usuarios", row.id)
    db.commit()
    return serialize(row)


@router.put("/{identity}")
def update_account(identity: int, data: UserUpdate, user=Depends(administrator), db: Session = Depends(get_db)):
    # Serializa alterações dos administradores da empresa no PostgreSQL.
    admins = db.scalars(select(User).where(User.academy_id == user.academy_id,
        User.role == "administrador", User.active.is_(True)).order_by(User.id).with_for_update()).all()
    row = db.scalar(select(User).where(User.id == identity, User.academy_id == user.academy_id))
    if not row:
        raise HTTPException(404, "Usuário não encontrado.")
    if row.role == "portfolio":
        raise HTTPException(403, "A conta pública é gerenciada pela configuração do ambiente.")
    if row.id == user.id:
        raise HTTPException(403, "Use Minha conta para alterar seus dados e senha. Seu perfil e acesso não podem ser alterados por você.")
    if row.role == "administrador" and row.active and (data.role != "administrador" or not data.active) and len(admins) <= 1:
        raise HTTPException(409, "Mantenha pelo menos um Administrador ativo na empresa.")
    available_email(db, str(data.email), row.id)
    invalidate = row.email != str(data.email) or row.role != data.role or row.active != data.active or data.password is not None
    row.name, row.email, row.role, row.active = data.name, str(data.email), data.role, data.active
    if data.password is not None:
        row.password_hash = hasher.hash(data.password.get_secret_value())
    if invalidate:
        db.execute(delete(AuthSession).where(AuthSession.user_id == row.id))
    audit(db, user, "atualizar_usuario", "usuarios", row.id,
        "Senha redefinida; sessões encerradas." if data.password else "Dados e acesso atualizados.")
    db.commit()
    return serialize(row)
