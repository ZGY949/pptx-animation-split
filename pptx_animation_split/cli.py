import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile

from . import __version__
from .operations import input_file, peek_file, split_file, unsupported_effects
from .verify import verify


def parser():
    result = argparse.ArgumentParser(
        prog='pptx-animation-split',
        description='把 PPTX 动画点击步骤拆成静态幻灯片；不覆盖源文件或已有输出。',
    )
    result.add_argument('--version', action='version', version=__version__)
    commands = result.add_subparsers(dest='command', required=True)
    split = commands.add_parser('split', help='拆分并自动校验结果')
    split.add_argument('source', help='源 .pptx 文件')
    split.add_argument('destination', help='尚不存在的输出 .pptx 路径')
    check = commands.add_parser('verify', help='校验已拆分文件的结构和动画状态')
    check.add_argument('source', help='源 .pptx 文件')
    check.add_argument('destination', help='拆分后的 .pptx 文件')
    peek = commands.add_parser('peek', help='按放映顺序抽查文字，不能判断可见性')
    peek.add_argument('source', help='.pptx 文件')
    peek.add_argument('pages', nargs='+', help='页码，例如 1 3-5')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'split':
            per_slide, notes, total = split_file(args.source, args.destination)
            for name, count, groups in per_slide:
                print('%s：%d 个动画组 → %d 页' % (name.rsplit('/', 1)[-1], groups, count))
            print('已保存 %d 页：%s' % (total, args.destination))
        elif args.command == 'verify':
            source = input_file(args.source)
            destination = input_file(args.destination)
            if verify(source, destination):
                return 1
            notes = unsupported_effects(source)
        else:
            peek_file(args.source, args.pages)
            return 0
        if notes:
            print('存在未支持效果；请人工核对，不能视为完整还原。', file=sys.stderr)
            return 3
        return 0
    except (OSError, ValueError, KeyError, AttributeError, ET.ParseError, zipfile.BadZipFile) as error:
        print('错误：%s' % error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
