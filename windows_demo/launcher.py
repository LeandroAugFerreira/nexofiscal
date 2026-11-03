"""Start a fresh, local-only NexoFiscal demonstration without developer configuration."""
import argparse
import ctypes
import hashlib
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
import webbrowser

BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(BUNDLE / "backend"), str(BUNDLE)]


def prepare(folder, origin):
    from app.core.config import Settings, settings
    Settings.model_config["env_file"] = None
    for field in Settings.model_fields:
        os.environ.pop(field.upper(), None)
    config_path = folder / "demo-settings.json"
    if not config_path.exists():
        with config_path.open("x", encoding="utf-8") as stream:
            json.dump({"schema": 1, "auxiliary_password": secrets.token_urlsafe(24)}, stream)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != 1 or len(config.get("auxiliary_password", "")) < 24:
        raise ValueError("Configuração local inválida")
    os.environ.update(DATABASE_URL="sqlite:///" + (folder / "nexofiscal-demo.db").as_posix(),
        ALLOWED_ORIGINS=origin, COOKIE_SECURE="false", DEMO_PASSWORD=config["auxiliary_password"],
        DEMO_ADMIN_PASSWORD="Adm@2026", DEMO_EMAIL="admin@nexofiscal.example.com", PORTFOLIO_ENABLED="true",
        PORTFOLIO_EMAIL="portfolio@nexofiscal.example.com", PORTFOLIO_PASSWORD="NexoFiscalDemo@2026")
    settings.cache_clear()
    from alembic import command
    from alembic.config import Config
    migration = Config()
    migration.set_main_option("script_location", str(BUNDLE / "backend/alembic"))
    command.upgrade(migration, "head")
    from contextlib import redirect_stdout
    from app.seed import seed
    from app.general_demo import provision as general_demo
    from app.portfolio import provision
    with redirect_stdout(io.StringIO()):
        seed(); general_demo(); provision()
    from app.main import app
    from starlette.staticfiles import StaticFiles
    from starlette.responses import FileResponse
    from starlette.exceptions import HTTPException
    class Frontend(StaticFiles):
        async def get_response(self, path, scope):
            normalized = path.replace("\\", "/").lstrip("/")
            if normalized == "api" or normalized.startswith("api/"):
                raise HTTPException(404)
            try:
                return await super().get_response(path, scope)
            except HTTPException as error:
                if error.status_code != 404 or normalized.startswith("assets/"):
                    raise
                return FileResponse(BUNDLE / "frontend/dist/index.html", media_type="text/html")
    app.mount("/", Frontend(directory=BUNDLE / "frontend/dist", html=True), name="desktop-frontend")
    return app


def window(url, folder, hidden=False):
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk(); root.title("NexoFiscal 0.1.0 — Demonstração local")
    root.geometry("640x405"); root.resizable(False, False); root.configure(bg="#101f2a")
    root.iconbitmap(str(BUNDLE / "windows_demo/nexofiscal.ico"))
    frame = tk.Frame(root, bg="#101f2a", padx=28, pady=24); frame.pack(fill="both", expand=True)
    for text, size, color in [("NexoFiscal", 27, "#89d8f2"), ("Emissão simulada de serviços • Sem validade fiscal", 11, "#f0eee8"),
        ("Pronto para usar. Mantenha esta janela aberta.", 11, "#bbc6cc"), (url, 12, "#89d8f2")]:
        tk.Label(frame, text=text, font=("Segoe UI", size), fg=color, bg="#101f2a").pack(anchor="w", pady=(0, 12))
    tk.Label(frame, text="Escolha Entrar no portfólio na tela de login.\nConta pública: portfolio@nexofiscal.example.com\nSenha: NexoFiscalDemo@2026", justify="left", font=("Segoe UI", 10), fg="#f0eee8", bg="#101f2a").pack(anchor="w", pady=8)
    style = ttk.Style(root); style.theme_use("clam"); style.configure("TButton", padding=9)
    controls = tk.Frame(frame, bg="#101f2a"); controls.pack(anchor="w", pady=18)
    help_page = BUNDLE / "help/nexofiscal-manual.html"
    if not help_page.is_file():
        help_page = BUNDLE.parent / "portfolio/nexofiscal-manual.html"
    for label, action in [("Abrir NexoFiscal", lambda: webbrowser.open(url + "/login")),
        ("Manual", lambda: webbrowser.open(help_page.as_uri())), ("Pasta de dados", lambda: os.startfile(str(folder))), ("Encerrar", root.destroy)]:
        ttk.Button(controls, text=label, command=action).pack(side="left", padx=(0, 8))
    tk.Label(frame, text="Base fictícia por instalação. Nenhuma conta pessoal do autor incluída.", font=("Segoe UI", 9), fg="#bbc6cc", bg="#101f2a").pack(anchor="w")
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    if hidden:
        root.withdraw()
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    folder = (args.data_dir or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NexoFiscal/0.1-demo").resolve()
    if folder.is_relative_to(BUNDLE) or "onedrive" in str(folder).lower():
        raise ValueError("A pasta de dados deve ficar fora do projeto e do OneDrive")
    folder.mkdir(parents=True, exist_ok=True)
    if args.self_test and (args.data_dir is None or any(folder.iterdir())):
        raise ValueError("Autoteste exige uma pasta nova e vazia explicitamente indicada")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel.CreateMutexW(None, False, "Local\\NexoFiscal-" + hashlib.sha256(str(folder).lower().encode()).hexdigest()[:24])
    if not mutex:
        raise OSError("Não foi possível proteger a pasta local")
    if ctypes.get_last_error() == 183:
        import re
        session = json.loads((folder / "session.json").read_text(encoding="utf-8"))
        if re.fullmatch(r"http://127\.0\.0\.1:\d+", session["url"]):
            webbrowser.open(session["url"])
        kernel.CloseHandle(ctypes.c_void_p(mutex)); return 0
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(folder / "nexofiscal.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8")], force=True)
    listener = socket.socket(); listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    server = thread = None
    try:
        try:
            listener.bind(("127.0.0.1", 5190))
        except OSError:
            listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        url = "http://127.0.0.1:" + str(listener.getsockname()[1])
        application = prepare(folder, url)
        import uvicorn
        server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", log_config=None, access_log=False, loop="asyncio", http="h11", ws="none"))
        errors = []
        def serve():
            try: server.run(sockets=[listener])
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=serve, daemon=True); thread.start()
        deadline = time.monotonic() + 120
        while not server.started:
            if errors or not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("A inicialização do serviço não foi concluída")
            time.sleep(.1)
        (folder / "session.json").write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
        if args.self_test:
            from windows_demo.selftest import run
            run(url, folder, BUNDLE, window)
        else:
            root = window(url, folder)
            if not args.no_browser: webbrowser.open(url + "/login")
            root.mainloop()
        return 0
    except Exception as error:
        logging.exception("NexoFiscal startup failed")
        if args.self_test:
            (folder / "self-test-error.json").write_text(json.dumps({"type": type(error).__name__, "message": str(error)}), encoding="utf-8")
        else:
            ctypes.windll.user32.MessageBoxW(None, "Não foi possível abrir. Consulte o log em:\n" + str(folder), "NexoFiscal", 16)
        return 1
    finally:
        if server: server.should_exit = True
        if thread: thread.join(timeout=15)
        if "app.database.session" in sys.modules:
            from app.database.session import engine
            engine.dispose()
        listener.close(); kernel.CloseHandle(ctypes.c_void_p(mutex))


if __name__ == "__main__":
    raise SystemExit(main())
