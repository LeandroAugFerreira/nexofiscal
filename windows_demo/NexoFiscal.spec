from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root/'frontend/dist'), 'frontend/dist'), (str(root/'windows_demo/nexofiscal.ico'), 'windows_demo'),
    (str(root/'windows_demo/help'), 'help')]
for path in (root/'backend/alembic').rglob('*'):
    if path.is_file() and path.suffix in ('.py','.mako') and '__pycache__' not in path.parts:
        datas.append((str(path),str(path.parent.relative_to(root))))
for package in ('fastapi','starlette','pydantic','uvicorn','alembic','argon2-cffi','reportlab','email-validator'):
    datas += copy_metadata(package)
datas += collect_data_files('reportlab', includes=['fonts/*'])
a=Analysis([str(root/'windows_demo/launcher.py')],pathex=[str(root),str(root/'backend')],datas=datas,
    hiddenimports=collect_submodules('app')+['windows_demo.selftest','uvicorn.logging','uvicorn.loops.asyncio',
        'uvicorn.protocols.http.h11_impl','uvicorn.lifespan.on','sqlalchemy.dialects.sqlite'],
    excludes=['pytest','_pytest','PyInstaller','psycopg','torch','numpy','pandas','matplotlib','IPython','notebook','scipy','edge_tts'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='NexoFiscal',debug=False,strip=False,upx=False,console=False,
    icon=str(root/'windows_demo/nexofiscal.ico'),version=str(root/'windows_demo/version.txt'))
