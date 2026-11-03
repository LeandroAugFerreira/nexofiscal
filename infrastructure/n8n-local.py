"""Configura/inicia a instalação n8n restrita ao projeto, sem imprimir segredos."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
NODE = RUNTIME / 'node-v24.22.0-win-x64' / 'node.exe'
ENTRY = RUNTIME / 'n8n' / 'node_modules' / 'n8n' / 'bin' / 'n8n'
EDITOR = 'http://127.0.0.1:5678'
sys.path.insert(0, str(ROOT / 'backend'))


def configuration():
    os.chdir(ROOT / 'backend')
    from app.core.config import settings
    settings.cache_clear()
    return settings()


def configure():
    path = ROOT / '.env'
    original = path.read_bytes()
    text = original.decode('utf-8-sig')
    cfg = configuration()
    if cfg.n8n_health_url and cfg.n8n_health_url != EDITOR + '/healthz':
        raise RuntimeError('Já existe outro n8n configurado. A configuração existente foi preservada.')
    smtp = [line for line in text.splitlines() if line.startswith('SMTP_')]
    updates = {'N8N_HEALTH_URL': EDITOR + '/healthz', 'N8N_WEBHOOK_URL': EDITOR + '/webhook/fitnota-payment',
        'N8N_EDITOR_URL': EDITOR, 'AUTOMATION_TOKEN': cfg.automation_token or secrets.token_urlsafe(48),
        'N8N_ENCRYPTION_KEY': cfg.n8n_encryption_key or secrets.token_hex(32)}
    if len(updates['AUTOMATION_TOKEN']) < 32:
        raise RuntimeError('O token existente é curto. Nenhum segredo foi sobrescrito.')
    newline = '\r\n' if '\r\n' in text else '\n'
    for key, value in updates.items():
        pattern = r'^' + re.escape(key) + r'=[^\r\n]*'
        if re.search(pattern, text, re.M):
            text = re.sub(pattern, lambda match: key + '=' + value, text, flags=re.M)
        else:
            text = text.rstrip('\r\n') + newline + key + '=' + value + newline
    assert smtp == [line for line in text.splitlines() if line.startswith('SMTP_')]
    encoded = text.encode('utf-8')
    path.write_bytes((b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + encoded)
    print('Conexão n8n configurada. Segredos locais preservados/gerados; SMTP inalterado.')


def environment():
    cfg = configuration()
    if not cfg.n8n_encryption_key:
        raise RuntimeError('Execute n8n-local.py configure antes de iniciar.')
    values = os.environ.copy()
    values.update({'N8N_USER_FOLDER': str(RUNTIME / 'n8n-user'), 'N8N_ENCRYPTION_KEY': cfg.n8n_encryption_key,
        'N8N_LISTEN_ADDRESS': '127.0.0.1', 'N8N_HOST': '127.0.0.1', 'N8N_PORT': '5678', 'N8N_PROTOCOL': 'http',
        'N8N_WEBHOOK_URL': EDITOR + '/', 'N8N_EDITOR_BASE_URL': EDITOR, 'N8N_SECURE_COOKIE': 'false',
        'N8N_DIAGNOSTICS_ENABLED': 'false', 'N8N_PERSONALIZATION_ENABLED': 'false',
        'N8N_VERSION_NOTIFICATIONS_ENABLED': 'false', 'N8N_TEMPLATES_ENABLED': 'false',
        'N8N_BLOCK_ENV_ACCESS_IN_NODE': 'true', 'N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES': 'true',
        'N8N_COMMUNITY_PACKAGES_ENABLED': 'false', 'N8N_UNVERIFIED_PACKAGES_ENABLED': 'false', 'N8N_LOG_LEVEL': 'warn',
        'GENERIC_TIMEZONE': 'America/Sao_Paulo', 'TZ': 'America/Sao_Paulo',
        'PATH': str(NODE.parent) + os.pathsep + values.get('PATH', '')})
    return values


def healthy():
    try:
        with httpx.Client(timeout=2) as client:
            return client.get(EDITOR + '/healthz').status_code == 200 and client.get(EDITOR + '/rest/settings').status_code == 200
    except httpx.HTTPError:
        return False


def existing_process():
    """Reconhece apenas o Node privado registrado; evita duplicação em partida lenta."""
    manifest = RUNTIME / 'n8n-process.json'
    if os.name != 'nt' or not manifest.exists():
        return False
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    try:
        identity = json.loads(manifest.read_text(encoding='utf-8'))['pid']
        handle = kernel.OpenProcess(0x1000, False, identity)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            name = ctypes.create_unicode_buffer(32768); length = wintypes.DWORD(len(name))
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259
                and kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(length))
                and Path(name.value).resolve() == NODE.resolve())
        finally:
            kernel.CloseHandle(handle)
    except (OSError, ValueError, KeyError):
        return False


def start():
    if healthy():
        print('n8n já disponível em ' + EDITOR)
        return
    if not NODE.is_file() or not ENTRY.is_file():
        raise RuntimeError('Execute infrastructure/instalar-n8n.ps1 antes de iniciar.')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 5678)) == 0:
            raise RuntimeError('Porta 5678 ocupada; nenhum processo foi alterado.')
    logs = ROOT / '.tmp'; logs.mkdir(exist_ok=True)
    flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
    process = None
    if existing_process():
        print('n8n já está inicializando; aguardando o mesmo processo.', flush=True)
    else:
        with (logs / 'n8n.stdout.log').open('ab') as output, (logs / 'n8n.stderr.log').open('ab') as errors:
            process = subprocess.Popen([str(NODE), str(ENTRY), 'start'], cwd=RUNTIME, env=environment(),
                stdout=output, stderr=errors, stdin=subprocess.DEVNULL, creationflags=flags)
        (RUNTIME / 'n8n-process.json').write_text(json.dumps({'pid': process.pid, 'editor': EDITOR}), encoding='utf-8')
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if healthy():
            print('n8n iniciado em ' + EDITOR)
            return
        if (process is not None and process.poll() is not None) or (process is None and not existing_process()):
            raise RuntimeError('n8n encerrou durante a inicialização. Consulte .tmp/n8n.stderr.log.')
        time.sleep(1)
    raise RuntimeError('n8n ainda não respondeu ao healthcheck; consulte os logs locais.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['configure', 'start'])
    args = parser.parse_args()
    try:
        {'configure': configure, 'start': start}[args.command]()
    except Exception as error:
        print(str(error) if isinstance(error, RuntimeError) else 'Falha na configuração/inicialização local. Credenciais omitidas.', file=sys.stderr)
        raise SystemExit(1)
