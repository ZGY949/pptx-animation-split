import argparse
import ast
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_RELATIVE = Path('skills/pptx-animation-split')
ENGINE_RELATIVE = SKILL_RELATIVE / 'scripts/pptx_animation_split'
sys.path.insert(0, str(ROOT))
from pptx_animation_split.bundle import file_hashes
from pptx_animation_split.updates import REPOSITORY, plugin_version


def project_version(root):
    tree = ast.parse((root / ENGINE_RELATIVE / '_version.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets):
            value = ast.literal_eval(node.value)
            plugin_version(value)
            return value
    raise ValueError('找不到项目版本号')


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def document_bytes(source, destination):
    text = source.read_text(encoding='utf-8')
    if source.name in {'TOOL.md', 'TOOL.en.md', 'SKILL_INSTALL.md', 'SKILL_INSTALL.en.md'} and source.parent.name == 'docs':
        stem = source.name.split('.')[0]
        target_stem = destination.name.split('.')[0]
        in_references = destination.parent.name == 'references'
        for old, new in {
            stem + '.md': target_stem + '.md', stem + '.en.md': target_stem + '.en.md',
            '../LICENSE': '../LICENSE' if in_references else 'LICENSE',
            '../ATTRIBUTION.md': '../ATTRIBUTION.md' if in_references else 'ATTRIBUTION.md',
            '../ATTRIBUTION.en.md': '../ATTRIBUTION.en.md' if in_references else 'ATTRIBUTION.en.md',
            'LIMITATIONS.md': 'LIMITATIONS.md' if in_references else 'docs/LIMITATIONS.md',
            'LIMITATIONS.en.md': 'LIMITATIONS.en.md' if in_references else 'docs/LIMITATIONS.en.md',
        }.items():
            text = text.replace('](' + old + ')', '](' + new + ')')
    for old, target in {
        'docs/source-baseline.json': 'docs/source-baseline.json',
        'VALIDATION.md': 'docs/VALIDATION.md',
        'VALIDATION.en.md': 'docs/VALIDATION.en.md',
        '../README.en.md': 'README.en.md',
    }.items():
        text = text.replace('](' + old + ')', '](' + REPOSITORY + '/blob/main/' + target + ')')
    return text.encode('utf-8')


def copy_document(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(document_bytes(source, destination))


def bundle_data(root, kind, version):
    files = file_hashes(root)
    files.pop('bundle.json', None)
    return {'schema_version': 1, 'kind': kind, 'version': version, 'files': files}


def bundle_manifest(root, kind, version):
    (root / 'bundle.json').write_bytes(json_bytes(bundle_data(root, kind, version)))


def sync_skill(root=ROOT, *, check=False):
    skill = root / SKILL_RELATIVE
    documents = {
        'LICENSE': 'LICENSE', 'ATTRIBUTION.md': 'ATTRIBUTION.md', 'ATTRIBUTION.en.md': 'ATTRIBUTION.en.md',
        'references/LIMITATIONS.md': 'docs/LIMITATIONS.md',
        'references/LIMITATIONS.en.md': 'docs/LIMITATIONS.en.md',
        'references/INSTALL.md': 'docs/SKILL_INSTALL.md',
        'references/INSTALL.en.md': 'docs/SKILL_INSTALL.en.md',
    }
    expected = {skill / target: document_bytes(root / source, skill / target) for target, source in documents.items()}
    expected[skill / 'references/click-order.json'] = (root / 'examples/click-order.json').read_bytes()
    changed = []

    def save(path, data):
        if path.is_file() and path.read_bytes() == data:
            return
        if check:
            raise ValueError('Skill 配套资源未同步：%s；请运行 python3 tools/sync_skill.py' % path.relative_to(root))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        changed.append(path.relative_to(root).as_posix())

    for path, data in expected.items():
        save(path, data)
    save(skill / 'bundle.json', json_bytes(bundle_data(skill, 'skill', project_version(root))))
    return changed


def main():
    parser = argparse.ArgumentParser(description='同步 Skill 的参考文档、许可证和文件清单；引擎只维护一份。')
    parser.add_argument('--check', action='store_true', help='只检查一致性，不写入文件')
    args = parser.parse_args()
    try:
        changed = sync_skill(check=args.check)
        print('Skill 资源一致。' if args.check else '已同步 %d 个文件。' % len(changed))
        return 0
    except (OSError, ValueError) as error:
        print('错误：%s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
