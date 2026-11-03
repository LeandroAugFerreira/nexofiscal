from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.database.session import engine
from app.api.routes import auth, business, insights, fiscal_center, documents_delivery, accounts, automations

app = FastAPI(title="NexoFiscal", version="0.1.0", description="Gestão e emissão de NFS-e para prestadores de serviços. Ambiente fiscal exclusivamente simulado.")
origins = settings().allowed_origins.split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"])


@app.middleware("http")
async def browser_security(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin not in origins:
        return JSONResponse(status_code=403, content={"detail": "Origem não autorizada."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(IntegrityError)
async def conflict_handler(request, exception):
    return JSONResponse(status_code=409, content={"detail": "Registro duplicado ou conflito de operação. Consulte o estado antes de tentar novamente."})


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exception):
    # Retorna a orientação de validação sem ecoar senhas ou outros dados recebidos.
    return JSONResponse(status_code=422, content={"detail": [
        {key: error[key] for key in ("loc", "msg", "type")} for error in exception.errors()]})


@app.get("/api/health", tags=["Operação"])
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.1.0", "database": engine.dialect.name, "fiscal": "simulador"}


app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(automations.router, prefix="/api")
app.include_router(business.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(fiscal_center.router, prefix="/api")
app.include_router(documents_delivery.router,prefix="/api")
