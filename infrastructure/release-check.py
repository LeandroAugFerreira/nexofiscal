"""Homologa o ZIP extraído; portas e banco separados da instalação do autor."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
COPY = ROOT / '.tmp/portfolio-release-check/NexoFiscal'
REPORT = ROOT / 'artifacts/release-check.json'


def wait(url):
    for _ in range(90):
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    raise RuntimeError('Serviço isolado não iniciou.')


def main():
    for port in (8012, 5182):
        with socket.socket() as connection:
            if connection.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(f'Porta isolada ocupada: {port}; nenhum processo foi encerrado.')
    python = COPY / 'backend/.venv/Scripts/python.exe'
    logs = ROOT / '.tmp/release-check-logs'
    logs.mkdir(exist_ok=True)
    env = {**os.environ, 'ALLOWED_ORIGINS': 'http://127.0.0.1:5182',
           'API_PROXY_TARGET': 'http://127.0.0.1:8012', 'FITNOTA_DEMO_URL': 'http://127.0.0.1:5182',
           'SMTP_HOST': '', 'SMTP_PASSWORD': '', 'SMTP_USERNAME': '', 'SMTP_FROM_EMAIL': ''}
    processes, streams = [], []
    results = {}
    try:
        def start(name, command, directory):
            stream = (logs / (name + '.log')).open('w', encoding='utf-8')
            streams.append(stream)
            process = subprocess.Popen(command, cwd=directory, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            processes.append(process)
            return process
        api = start('api', [str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8012', '--no-access-log'], COPY / 'backend')
        vite = start('vite', ['node', str(COPY / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5182'], COPY / 'frontend')
        tests = start('pytest', [str(python), '-m', 'pytest', '-q'], COPY / 'backend')
        build = start('build', ['node', str(COPY / 'frontend/node_modules/vite/bin/vite.js'), 'build'], COPY / 'frontend')
        wait('http://127.0.0.1:8012/api/health')
        wait('http://127.0.0.1:5182/api/health')
        capture = start('capture', ['node', str(ROOT / 'infrastructure/portfolio-flow-smoke.cjs')], ROOT)
        for name, process in [('build', build), ('capture', capture), ('pytest', tests)]:
            code = process.wait(timeout=600)
            results[name] = 'passed' if code == 0 else 'failed'
            print(name + ': ' + results[name], flush=True)
        migration = subprocess.run([str(python), '-m', 'alembic', 'check'], cwd=COPY / 'backend',
                                   env=env, capture_output=True, text=True)
        results['alembic'] = 'passed' if migration.returncode == 0 else 'failed'
        results.update(date='2026-10-18', database='SQLite isolado, criado pelo setup',
                       smtp='desabilitado; endpoint de envio bloqueado na captura', ports=[8012, 5182])
        REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        if 'failed' in results.values():
            raise RuntimeError('Uma verificação falhou; consulte os logs locais.')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
        for stream in streams:
            stream.close()


if __name__ == '__main__':
    main()
