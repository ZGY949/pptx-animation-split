from pathlib import Path
import sys


def main():
    sys.dont_write_bytecode = True
    here = Path(__file__).resolve().parent
    if (here / 'pptx_animation_split' / 'cli.py').is_file():
        engine_root = here
        bundle_root = here if (here / 'bundle.json').is_file() else here.parent
        if not (bundle_root / 'bundle.json').is_file():
            print('缺少安装包清单；请重新解压完整安装包。', file=sys.stderr)
            return 1
    else:
        engine_root = here.parents[2]
        bundle_root = None
        if not (engine_root / 'pyproject.toml').is_file() or not (engine_root / 'pptx_animation_split' / 'cli.py').is_file():
            print('找不到配套工具。源码 Skill 需要完整项目；独立安装请使用 Release 中的 Skill 安装包。', file=sys.stderr)
            return 1
    sys.path.insert(0, str(engine_root))
    try:
        from pptx_animation_split.bundle import verify_bundle
        metadata = verify_bundle(bundle_root) if bundle_root else {'kind': 'skill'}
        from pptx_animation_split.cli import main as run_cli
        return run_cli(notify_updates=metadata['kind'] == 'skill')
    except (OSError, ValueError, KeyError) as error:
        print('错误：%s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
