import hashlib
import json
from pathlib import Path, PurePosixPath

from . import __version__


def file_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file() and path.name != '.DS_Store' and path.suffix not in {'.pyc', '.pyo'}
        and not any(part in {'__pycache__', '.git'} or part.endswith(('.egg-info', '.dist-info')) for part in path.relative_to(root).parts)
    }


def verify_bundle(root):
    root = Path(root)
    data = json.loads((root / 'bundle.json').read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('version') != __version__ or data.get('kind') not in {'tool', 'skill'}:
        raise ValueError('安装包版本不一致；请重新安装完整的同版本安装包')
    expected = data.get('files')
    if not isinstance(expected, dict) or not expected:
        raise ValueError('安装包文件清单无效')
    for name, digest in expected.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError('安装包文件清单格式无效')
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('安装包文件路径无效')
        path = root.joinpath(*relative.parts)
        linked = any(root.joinpath(*relative.parts[:depth]).is_symlink() for depth in range(1, len(relative.parts) + 1))
        if linked or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('安装包文件缺失或已修改：%s；请重新安装完整安装包' % name)
    engine = root / ('scripts' if data['kind'] == 'skill' else '') / 'pptx_animation_split'
    actual = {path.relative_to(root).as_posix() for path in engine.rglob('*') if path.is_file() and path.suffix == '.py'}
    declared = {name for name in expected if name.startswith(engine.relative_to(root).as_posix() + '/') and name.endswith('.py')}
    if actual != declared:
        raise ValueError('安装包混入其他版本的程序文件；请重新安装完整安装包')
    return data
