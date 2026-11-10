import argparse
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    'README.md', 'README.en.md', 'ATTRIBUTION.md', 'CONTRIBUTING.md', 'pyproject.toml',
    '.gitignore', 'LICENSE',
}
SOURCE_DIRECTORIES = {
    'pptx_animation_split', 'tests', 'examples', 'docs', 'tools', '.github',
}
TEXT_SUFFIXES = {'.py', '.md', '.toml', '.json', '.txt', '.yml', '.yaml'}


def source_files():
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink() or '__pycache__' in relative.parts:
            continue
        if len(relative.parts) == 1 and path.name in ROOT_FILES:
            yield path
        elif relative.parts[0] in SOURCE_DIRECTORIES and (
            path.suffix in TEXT_SUFFIXES or relative.as_posix() in {'examples/demo.pptx', 'examples/animation-cases.pptx', 'examples/interaction-repeat-cases.pptx'}
        ):
            yield path


def main():
    parser = argparse.ArgumentParser(description='按源码清单生成 ZIP，不含真实课件和本地检查结果。')
    parser.add_argument('destination', type=Path, help='新的 ZIP 输出路径')
    args = parser.parse_args()
    paths = list(source_files())
    with args.destination.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in paths:
                    archive.write(path, 'pptx-animation-split/' + path.relative_to(ROOT).as_posix())
        except BaseException:
            stream.close()
            args.destination.unlink(missing_ok=True)
            raise
    print('已写入 %d 个文件：%s' % (len(paths), args.destination))


if __name__ == '__main__':
    main()
