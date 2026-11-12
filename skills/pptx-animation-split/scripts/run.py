from pathlib import Path
import sys


def main():
    sys.dont_write_bytecode = True
    here = Path(__file__).resolve().parent
    bundle_root = here if (here / 'bundle.json').is_file() else here.parent
    if not (here / 'pptx_animation_split' / 'cli.py').is_file() or not (bundle_root / 'bundle.json').is_file():
        print('缺少配套引擎或文件清单。请重新安装完整 Skill；源码开发后先运行 tools/sync_skill.py。', file=sys.stderr)
        return 1
    sys.path.insert(0, str(here))
    try:
        from pptx_animation_split.bundle import verify_bundle
        metadata = verify_bundle(bundle_root)
        from pptx_animation_split.cli import main as run_cli
        return run_cli(notify_updates=metadata['kind'] == 'skill')
    except (OSError, ValueError, KeyError) as error:
        print('错误：%s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
