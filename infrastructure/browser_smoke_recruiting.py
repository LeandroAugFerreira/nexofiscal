"""Smoke Playwright seguro do NexoFiscal: login, central e nova solicitação.

Executado somente em runner CI com banco SQLite temporário e credenciais
sintéticas aleatórias. NÃO emite nota, transmite documentos, executa SMTP/n8n,
publica servidor nem lê .env da máquina do autor.
"""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
API = "http://127.0.0.1:8018"
SITE = "http://127.0.0.1:5188"
ARTIFACTS = ROOT / "artifacts" / "browser"


def online(url: str, timeout: int = 90) -> None:
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        try:
            with urllib.request.urlopen(url, timeout=3) as result:
                if result.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.4)
    raise RuntimeError("Serviço da demonstração não iniciou no loopback.")


def launch(command, cwd, env, output):
    handle = output.open("w", encoding="utf-8")
    process = subprocess.Popen(command, cwd=cwd, env=env,
                               stdout=handle, stderr=subprocess.STDOUT)
    return process, handle


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nexofiscal-browser-qa-") as temporary:
        # Expurgar referências a instalações anteriores, inclusive SMTP e n8n.
        env = os.environ.copy()
        for key in tuple(env):
            if (key.startswith(("N8N_", "SMTP_", "DEMO_", "PORTFOLIO_",
                                "AUTOMATION_", "DATABASE_URL", "FITNOTA_"))
                or key in {"COOKIE_SECURE", "ALLOWED_ORIGINS"}):
                env.pop(key, None)
        password = secrets.token_urlsafe(30)
        env.update({
            "DATABASE_URL": "sqlite:///" + (Path(temporary) / "nexofiscal-qa.sqlite").as_posix(),
            "DEMO_PASSWORD": password,
            "DEMO_ADMIN_PASSWORD": password,
            "DEMO_EMAIL": "avaliador@example.com",
            "PORTFOLIO_ENABLED": "false",
            "AUTOMATION_TOKEN": "",
            "N8N_WEBHOOK_URL": "",
            "N8N_HEALTH_URL": "",
            "SMTP_HOST": "",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_FROM_EMAIL": "",
            "ALLOWED_ORIGINS": SITE,
            "API_PROXY_TARGET": API,
        })
        subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini",
                        "upgrade", "head"], cwd=BACKEND, env=env,
                       check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, timeout=120)
        subprocess.run([sys.executable, "-m", "app.seed"], cwd=BACKEND,
                       env=env, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, timeout=180)
        api, api_handle = launch(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", "8018", "--no-access-log"],
            BACKEND, env, Path(temporary) / "api.log"
        )
        vite, vite_handle = launch(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1",
             "--port", "5188", "--strictPort"],
            FRONTEND, env, Path(temporary) / "vite.log"
        )
        try:
            online(API + "/api/health")
            online(SITE)
            with sync_playwright() as browser_tool:
                browser = browser_tool.chromium.launch(headless=True)
                context = browser.new_context(locale="pt-BR",
                                              viewport={"width": 1350, "height": 900})
                page = context.new_page()
                page.set_default_timeout(18000)
                try:
                    page.goto(SITE, wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Vamos começar?")).to_be_visible(
                        timeout=25000)
                    page.get_by_role("textbox", name="E-mail").fill(
                        "avaliador@example.com")
                    page.get_by_label("Senha", exact=True).fill(password)
                    page.get_by_role("button", name="Entrar no NexoFiscal").click()
                    try:
                        expect(page.get_by_role("heading", name="Central de emissão")).to_be_visible(
                            timeout=30000)
                    except AssertionError:
                        # Texto da interface, não inputs/segredos, para diagnosticar o CI.
                        print("UI após login (somente texto):", page.locator("body").inner_text()[:1200])
                        raise
                    health = context.request.get(SITE + "/api/health")
                    if not health.ok or health.json()["fiscal"] != "simulador":
                        raise AssertionError("API fiscal precisa permanecer no simulador.")
                    overview = context.request.get(SITE + "/api/fiscal/overview")
                    if not overview.ok:
                        raise AssertionError(f"Central autenticada retornou HTTP {overview.status}")
                    page.screenshot(path=str(ARTIFACTS / "nexofiscal-central-sintetica.png"),
                                    full_page=True)
                    page.goto(SITE + "/emitir", wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Emitir NFS-e")).to_be_visible(
                        timeout=25000)
                    expect(page.get_by_role("button", name="Emissão avulsa")).to_be_visible()
                    page.screenshot(path=str(ARTIFACTS / "nexofiscal-emissao-sintetica.png"),
                                    full_page=True)
                    print("PASS: login via formulário React e cookies de sessão reais.")
                    print("PASS: Central e API autenticadas, provider exclusivamente simulador.")
                    print("PASS: página de emissão avulsa navegável, sem executar emissão.")
                except Exception:
                    page.screenshot(path=str(ARTIFACTS / "nexofiscal-falha-sintetica.png"),
                                    full_page=True)
                    raise
                finally:
                    context.close()
                    browser.close()
        finally:
            for process in (vite, api):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            api_handle.close()
            vite_handle.close()


if __name__ == "__main__":
    main()
