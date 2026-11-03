"""Distribuição por lista de arquivos permitidos, sem dados ou configuração local."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def source_files():
    roots = ['backend/app', 'backend/alembic', 'backend/tests', 'frontend/src',
             'infrastructure', 'docs', 'n8n/workflows', 'n8n/docs', 'windows_demo']
    extensions = {'.py', '.jsx', '.js', '.css', '.html', '.md', '.txt', '.ini',
                  '.json', '.mako', '.ps1', '.cjs', '.conf', '.png', '.jpg', '.svg', '.spec', '.ico'}
    files = set()
    for name in roots:
        for path in (ROOT / name).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_file() and path.suffix in extensions and not any(
                part.startswith('.') or part in {'__pycache__', 'node_modules', 'backups'}
                for part in relative.parts):
                files.add(path)
    for name in ['README.md', '.gitignore', '.dockerignore', '.env.example',
                 'docker-compose.yml', 'Iniciar NexoFiscal.cmd', 'backend/requirements.txt',
                 'backend/requirements-dev.txt', 'backend/alembic.ini', 'backend/Dockerfile',
                 'backend/.dockerignore', 'frontend/package.json', 'frontend/package-lock.json',
                 'frontend/vite.config.js', 'frontend/index.html', 'frontend/Dockerfile',
                 'frontend/.dockerignore']:
        path = ROOT / name
        if path.is_file():
            files.add(path)
    return sorted(files)


def main():
    destination = ROOT / 'output' / 'release'
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'NexoFiscal-codigo-fonte.zip'
    files = source_files()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, 'NexoFiscal/' + path.relative_to(ROOT).as_posix())
    report = {'archive': archive.name, 'files': len(files), 'bytes': archive.stat().st_size,
              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'exclusions': ['credenciais locais', 'bancos', 'backups', 'logs', 'dependências', 'runtime n8n']}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
