import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pptx_animation_split.bundle import file_hashes, verify_bundle
from pptx_animation_split.updates import CLI_API, REPOSITORY, plugin_version
from tools.package_source import source_files


SKILL = 'pptx-animation-split'
MANIFEST = 'release.json'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_document(source, destination):
    text = source.read_text(encoding='utf-8')
    if source.name in {'TOOL.md', 'TOOL.en.md', 'SKILL.md', 'SKILL.en.md'} and source.parent.name == 'docs':
        stem = source.name.split('.')[0]
        for old, new in {
            stem + '.md': 'README.md', stem + '.en.md': 'README.en.md',
            '../LICENSE': 'LICENSE', '../ATTRIBUTION.md': 'ATTRIBUTION.md', '../ATTRIBUTION.en.md': 'ATTRIBUTION.en.md',
            'LIMITATIONS.md': 'docs/LIMITATIONS.md', 'LIMITATIONS.en.md': 'docs/LIMITATIONS.en.md',
        }.items():
            text = text.replace('](' + old + ')', '](' + new + ')')
    for old, target in {
        'docs/source-baseline.json': 'docs/source-baseline.json',
        'VALIDATION.md': 'docs/VALIDATION.md',
        'VALIDATION.en.md': 'docs/VALIDATION.en.md',
        '../README.en.md': 'README.en.md',
    }.items():
        text = text.replace('](' + old + ')', '](' + REPOSITORY + '/blob/main/' + target + ')')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding='utf-8')


def source_state(root):
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root, text=True))
        return {'commit': commit, 'dirty': dirty}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'dirty': True}


def project_version(root):
    tree = ast.parse((root / 'pptx_animation_split' / '__init__.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets):
            value = ast.literal_eval(node.value)
            plugin_version(value)
            return value
    raise ValueError('找不到项目版本号')


def python_requirement(root):
    text = (root / 'pyproject.toml').read_text(encoding='utf-8')
    match = re.search(r'^requires-python\s*=\s*["\']>=([0-9]+)\.([0-9]+)["\']\s*$', text, re.MULTILINE)
    if not match:
        raise ValueError('请同步更新打包器对 requires-python 的解析规则')
    return [int(part) for part in match.groups()]


def bundle_manifest(root, kind, version):
    write_json(root / 'bundle.json', {
        'schema_version': 1, 'kind': kind, 'version': version, 'files': file_hashes(root),
    })


def copy_engine(snapshot, destination):
    destination.mkdir(parents=True)
    engine = snapshot / 'pptx_animation_split'
    for path in sorted(engine.rglob('*')):
        if path.is_file():
            copy_file(path, destination / path.relative_to(engine))


def add_licenses(snapshot, destination):
    for name in ('LICENSE', 'ATTRIBUTION.md', 'ATTRIBUTION.en.md'):
        copy_document(snapshot / name, destination / name)


def make_packages(snapshot, directory, version):
    tool = directory / ('pptx-animation-split-' + version + '-tool')
    tool.mkdir()
    copy_engine(snapshot, tool / 'pptx_animation_split')
    copy_file(snapshot / 'skills' / SKILL / 'scripts' / 'run.py', tool / 'run.py')
    add_licenses(snapshot, tool)
    for suffix in ('', '.en'):
        copy_document(snapshot / 'docs' / ('TOOL' + suffix + '.md'), tool / ('README' + suffix + '.md'))
        copy_document(snapshot / 'docs' / ('LIMITATIONS' + suffix + '.md'), tool / ('docs/LIMITATIONS' + suffix + '.md'))
    copy_file(snapshot / 'examples/demo.pptx', tool / 'examples/demo.pptx')
    copy_file(snapshot / 'examples/click-order.json', tool / 'examples/click-order.json')
    bundle_manifest(tool, 'tool', version)

    plugin = directory / ('pptx-animation-split-' + version + '-skill')
    skill = plugin / 'skills' / SKILL
    skill.mkdir(parents=True)
    for path in (snapshot / 'skills' / SKILL).rglob('*'):
        if path.is_file():
            copy_file(path, skill / path.relative_to(snapshot / 'skills' / SKILL))
    copy_engine(snapshot, skill / 'scripts/pptx_animation_split')
    add_licenses(snapshot, skill)
    add_licenses(snapshot, plugin)
    for suffix in ('', '.en'):
        copy_document(snapshot / 'docs' / ('SKILL' + suffix + '.md'), plugin / ('README' + suffix + '.md'))
        copy_document(snapshot / 'docs' / ('LIMITATIONS' + suffix + '.md'), skill / ('references/LIMITATIONS' + suffix + '.md'))
    copy_file(snapshot / 'examples/click-order.json', skill / 'references/click-order.json')
    bundle_manifest(skill, 'skill', version)
    identity = {
        'name': SKILL, 'version': plugin_version(version),
        'description': 'Split PowerPoint animation steps into static slides with a bundled Python engine.',
        'author': {'name': 'ZGY949'}, 'homepage': REPOSITORY, 'repository': REPOSITORY, 'license': 'MIT',
    }
    write_json(plugin / 'plugin.json', {
        '$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', **identity,
    })
    write_json(plugin / '.codex-plugin/plugin.json', {**identity, 'skills': './skills/'})
    write_json(plugin / '.agents/plugins/marketplace.json', {
        'name': 'pptx-animation-split-local',
        'plugins': [{
            'name': SKILL, 'source': {'source': 'local', 'path': './'},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity',
        }],
    })
    return {'tool': tool, 'skill': plugin}


def archive_directory(root, destination):
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                item = zipfile.ZipInfo(root.name + '/' + path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, path.read_bytes())


def validate_packages(packages, snapshot, directory, version):
    engine_hashes = file_hashes(snapshot / 'pptx_animation_split')
    report = {}
    samples = {'demo.pptx': 3, 'animation-cases.pptx': 13, 'interaction-repeat-cases.pptx': 8}
    for kind, package in packages.items():
        if kind == 'skill':
            for name in ('plugin.json', '.codex-plugin/plugin.json'):
                identity = json.loads((package / name).read_text(encoding='utf-8'))
                if identity.get('name') != SKILL or identity.get('version') != plugin_version(version):
                    raise ValueError('插件清单版本与实际工具版本不一致')
        bundle = package if kind == 'tool' else package / 'skills' / SKILL
        metadata = verify_bundle(bundle)
        if metadata['version'] != version:
            raise ValueError('安装包版本与发布版本不一致')
        engine = bundle / ('scripts' if kind == 'skill' else '') / 'pptx_animation_split'
        hashes = file_hashes(engine)
        if hashes != engine_hashes:
            raise ValueError('安装包引擎与同一份源码不一致')
        launcher = bundle / ('scripts/run.py' if kind == 'skill' else 'run.py')
        before = file_hashes(package)
        workspace = directory / (kind + '-checks')
        workspace.mkdir()

        def run(*args):
            result = subprocess.run([sys.executable, '-I', '-B', str(launcher), *map(str, args)], cwd=workspace, text=True, capture_output=True, timeout=60)
            if result.returncode:
                raise ValueError('%s 安装包执行失败：%s\n%s' % (kind, ' '.join(map(str, args)), result.stderr + result.stdout))
            return result.stdout

        if run('--version').strip() != version:
            raise ValueError('安装包实际入口版本不一致')
        for name, expected in samples.items():
            source = snapshot / 'examples' / name
            output = workspace / name
            run('--no-update-check', 'split', source, output)
            run('verify', source, output)
            with zipfile.ZipFile(output) as archive:
                count = sum(bool(re.fullmatch(r'ppt/slides/slide\d+\.xml', part)) for part in archive.namelist())
            if count != expected:
                raise ValueError('样例状态数不符：%s' % name)
        source = snapshot / 'examples/interaction-repeat-cases.pptx'
        route = snapshot / 'examples/click-order.json'
        output = workspace / 'custom.pptx'
        run('--no-update-check', 'split', source, output, '--click-order', route)
        run('verify', source, output, '--click-order', route)
        run('peek', workspace / 'demo.pptx', '1', '3')
        if before != file_hashes(package):
            raise ValueError('运行过程修改了安装包文件')
        report[kind] = {'version': version, 'sample_states': samples, 'custom_click_route': True, 'package_unchanged': True}
    return engine_hashes, report


def build_release(destination, *, local=False, root=ROOT):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('输出目录已存在，请选择新目录：%s' % destination)
    state = source_state(root)
    version = project_version(root)
    if not local:
        if state['dirty'] or not state['commit']:
            raise ValueError('正式构建需要干净的 Git 提交；本地试装请明确使用 --local')
        try:
            tag_commit = subprocess.check_output(['git', 'rev-parse', 'refs/tags/v' + version + '^{commit}'], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        except subprocess.CalledProcessError as error:
            raise ValueError('正式构建需要指向当前提交的 v%s 标签' % version) from error
        if tag_commit != state['commit']:
            raise ValueError('版本标签没有指向当前提交')
    paths = list(source_files(root))
    before = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pptx-release-') as temporary:
        stage = Path(temporary)
        snapshot = stage / 'source'
        for path in paths:
            copy_file(path, snapshot / path.relative_to(root))
        packages = make_packages(snapshot, stage, version)
        engine, checks = validate_packages(packages, snapshot, stage, version)
        artifacts = stage / 'artifacts'
        artifacts.mkdir()
        assets = {}
        for kind, package in packages.items():
            name = package.name + '.zip'
            archive_directory(package, artifacts / name)
            assets[kind] = {'name': name, 'sha256': hashlib.sha256((artifacts / name).read_bytes()).hexdigest()}
        write_json(artifacts / MANIFEST, {
            'schema_version': 1, 'version': version, 'plugin_version': plugin_version(version),
            'cli_api': CLI_API, 'requires_python': python_requirement(snapshot),
            'publishable': not local, 'source': state, 'assets': assets,
            'engine_sha256': hashlib.sha256(json.dumps(engine, sort_keys=True).encode()).hexdigest(),
        })
        write_json(artifacts / 'validation.json', {'version': version, 'checks': checks, 'source': state, 'local_build': local})
        lines = [hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name for path in sorted(artifacts.iterdir())]
        (artifacts / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        after = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files(root)}
        if before != after or source_state(root) != state:
            raise ValueError('构建过程中源码发生变化，未交付安装包；请重新构建')
        destination.mkdir()
        copied = []
        try:
            for path in artifacts.iterdir():
                target = destination / path.name
                with target.open('xb') as output:
                    copied.append(target)
                    output.write(path.read_bytes())
        except BaseException:
            for path in copied:
                path.unlink(missing_ok=True)
            try:
                destination.rmdir()
            except OSError:
                pass
            raise
    return {'version': version, 'destination': str(destination), 'publishable': not local, 'assets': assets, 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description='从同一份源码构建工具包和 Skill 包，完成隔离验证后交付；不上传或发布。')
    parser.add_argument('destination', type=Path, help='尚不存在的输出目录')
    parser.add_argument('--local', action='store_true', help='允许未提交源码，仅生成不可用于正式发布的本地试装包')
    args = parser.parse_args()
    try:
        print(json.dumps(build_release(args.destination, local=args.local), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('错误：%s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
