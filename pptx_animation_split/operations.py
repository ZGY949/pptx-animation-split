import os
from pathlib import Path
import tempfile
import zipfile

from ._core import parse_slide_animation, slide_order, split_pptx
from .verify import verify
import xml.etree.ElementTree as ET


def input_file(value):
    path = Path(value).expanduser()
    if path.suffix.lower() != '.pptx':
        raise ValueError('仅支持 .pptx 文件，不支持 .ppt、.pptm 或加密文件')
    if not path.is_file():
        raise ValueError('找不到文件：%s' % path)
    return path


def unsupported_effects(source):
    notes = []
    with zipfile.ZipFile(source) as archive:
        for name in slide_order(archive):
            _, warnings = parse_slide_animation(ET.fromstring(archive.read(name)))
            notes.extend((name, warning) for warning in warnings)
    return notes


def split_file(source, destination, log=print, allow_partial=False):
    source = input_file(source)
    destination = Path(destination).expanduser()
    if destination.suffix.lower() != '.pptx':
        raise ValueError('输出文件必须使用 .pptx 扩展名')
    if source.resolve() == destination.resolve() or (
        destination.exists() and os.path.samefile(source, destination)
    ):
        raise ValueError('输出路径不能与源文件相同；请为拆分结果使用新文件名')
    if os.path.lexists(destination):
        raise FileExistsError('输出文件已存在，请使用新文件名：%s' % destination)
    if not destination.parent.is_dir():
        raise ValueError('输出目录不存在：%s' % destination.parent)
    warnings = unsupported_effects(source)
    if warnings and not allow_partial:
        details = '\n'.join('%s：%s' % (part, warning) for part, warning in warnings[:30])
        raise ValueError('存在未支持动画，未生成输出。仅在需要人工核对的草稿时使用 --allow-partial。\n' + details)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix='.pptx-split-', suffix='.pptx', dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        per_slide, notes, total = split_pptx(source, temporary, log=log)
        if verify(source, temporary, log=log):
            raise ValueError('结果未通过结构或动画状态校验，未保存输出文件')
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return per_slide, notes, total


def peek_file(source, pages, log=print):
    source = input_file(source)
    with zipfile.ZipFile(source) as archive:
        slides = slide_order(archive)
        selected = []
        for value in pages:
            parts = value.split('-')
            if len(parts) not in (1, 2) or not all(part.isdecimal() for part in parts):
                raise ValueError('页码应为正整数或范围，例如 3 或 3-5')
            start, end = int(parts[0]), int(parts[-1])
            if start < 1 or end < start or end > len(slides):
                raise ValueError('页码超出范围，文件共有 %d 页' % len(slides))
            selected.extend(range(start, end + 1))
        for number in selected:
            root = ET.fromstring(archive.read(slides[number - 1]))
            texts = [node.text for node in root.iter(
                '{http://schemas.openxmlformats.org/drawingml/2006/main}t'
            ) if node.text]
            log('--- 第%d页 --- %s' % (number, '|'.join(texts)[:400]))
    log('文本抽查包含透明占位文字，不能据此判断文字是否可见。')
