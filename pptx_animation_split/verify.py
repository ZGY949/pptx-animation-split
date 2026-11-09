import io
import copy
import posixpath
import zipfile
import xml.etree.ElementTree as ET

from ._core import A, CT, MC, P, R, VML, SHAPE_TAGS, active_animation_groups, all_animation_groups, animation_visibility, apply_emphasis, parse_slide_animation, relationship_part, resolve_part, scale_group_text, slide_order


def signature(element):
    if element is None:
        return None
    return (element.tag, tuple(sorted(element.attrib.items())), element.text or '',
            tuple(signature(child) for child in element))


def transient_visibility_step(groups, step):
    targets = {}
    for effect in groups[step]:
        if effect['cls'] not in ('entr', 'exit') or not effect.get('spid') or effect.get('changes'):
            return False
        key = (effect['spid'], effect.get('prg'))
        targets.setdefault(key, set()).add(effect['cls'])
    return bool(targets) and all(kinds == {'entr', 'exit'} for kinds in targets.values()) and (
        animation_visibility(groups, step - 1) == animation_visibility(groups, step))


def shape_index(root):
    result = {}
    tree = root.find(P + 'cSld/' + P + 'spTree')
    tags = {P + tag for tag in SHAPE_TAGS}

    def walk(parent, branch=(), ancestors=()):
        for child in parent:
            next_branch = branch
            next_ancestors = ancestors
            if child.tag in (MC + 'Choice', MC + 'Fallback'):
                next_branch += ((child.tag, child.get('Requires', '')),)
            if child.tag in tags:
                nv = next((n for n in child if n.tag.startswith(P + 'nv')), None)
                cnv = nv.find(P + 'cNvPr') if nv is not None else None
                if cnv is not None:
                    sid = cnv.get('id')
                    key = (sid, next_branch)
                    if key in result:
                        raise ValueError('同一兼容分支中出现重复对象编号 %s' % sid)
                    result[key] = (child, ancestors)
                    next_ancestors += (sid,)
            walk(child, next_branch, next_ancestors)

    if tree is not None:
        walk(tree)
    return result


def transparent_paragraph(paragraph):
    props = []
    for element in paragraph.iter():
        if element.tag in (A + 'r', A + 'fld', A + 'br'):
            prop = element.find(A + 'rPr')
            if prop is None:
                return False
            props.append(prop)
    props.extend(paragraph.findall(A + 'pPr/' + A + 'defRPr'))
    props.extend(paragraph.findall(A + 'endParaRPr'))
    return bool(props) and all(
        prop.find(A + 'solidFill/' + A + 'srgbClr/' + A + 'alpha') is not None
        and prop.find(A + 'solidFill/' + A + 'srgbClr/' + A + 'alpha').get('val') == '0'
        for prop in props)


def check_state(source_root, output_root, groups, step, slide_size=None):
    errors = []
    source = shape_index(source_root)
    output = shape_index(output_root)
    whole_events = {}
    paragraph_events = {}
    for group_index, effects in enumerate(all_animation_groups(groups), -1):
        for effect in effects:
            if effect['cls'] not in ('entr', 'exit') or not effect['spid']:
                continue
            sid = effect['spid']
            if not any(key[0] == sid for key in source):
                errors.append('源动画目标不存在：%s' % sid)
            if effect['prg'] is None:
                whole_events.setdefault(sid, []).append((group_index, effect['cls'], effect.get('order', 0)))
            else:
                for paragraph_index in range(effect['prg'][0], effect['prg'][1] + 1):
                    key = (sid, paragraph_index)
                    paragraph_events.setdefault(key, []).append((group_index, effect['cls'], effect.get('order', 0)))

    def visible_after(events):
        visible = min(events, key=lambda event: event[2])[1] == 'exit'
        for group_index, kind, _ in events:
            if group_index <= step:
                visible = kind == 'entr'
        return visible

    whole = {sid: visible_after(events) for sid, events in whole_events.items()}
    paragraphs = {key: visible_after(events) for key, events in paragraph_events.items()}

    for key, (original, ancestors) in source.items():
        sid = key[0]
        visible = all(whole.get(target, True) for target in ancestors + (sid,))
        if not visible:
            if key in output:
                errors.append('对象 %s 在此步骤应隐藏但仍显示' % sid)
            continue
        if key not in output:
            errors.append('对象 %s 应显示但缺失' % sid)
            continue
        actual = output[key][0]
        original = copy.deepcopy(original)
        reference = copy.deepcopy(original)
        for effects in active_animation_groups(groups, step):
            for effect in effects:
                if effect['spid'] in ancestors:
                    for change in effect.get('changes') or []:
                        if change['kind'] == 'scale':
                            scale_group_text(original, change['x'] / 100000)
                if effect['cls'] in ('emph', 'path') and effect['spid'] == sid and effect.get('changes'):
                    apply_emphasis(original, effect, slide_size, reference)
        for prop in ('spPr', 'grpSpPr', 'xfrm', 'blipFill', 'style'):
            if signature(original.find(P + prop)) != signature(actual.find(P + prop)):
                errors.append('对象 %s 的位置、图片裁剪或样式改变：%s' % (sid, prop))
        original_body = original.find(P + 'txBody')
        actual_body = actual.find(P + 'txBody')
        if original_body is None:
            continue
        if actual_body is None:
            errors.append('对象 %s 的文本框缺失' % sid)
            continue
        for prop in ('bodyPr', 'lstStyle'):
            if signature(original_body.find(A + prop)) != signature(actual_body.find(A + prop)):
                errors.append('对象 %s 的文字排版属性改变' % sid)
        original_paras = original_body.findall(A + 'p')
        actual_paras = actual_body.findall(A + 'p')
        if len(original_paras) != len(actual_paras):
            errors.append('对象 %s 的段落数量改变，可能导致文字移位' % sid)
            continue
        for pi, (before, after) in enumerate(zip(original_paras, actual_paras)):
            if not paragraphs.get((sid, pi), True):
                if [(x.tag, x.text) for x in before.iter() if x.tag.endswith('}t')] != [(x.tag, x.text) for x in after.iter() if x.tag.endswith('}t')]:
                    errors.append('对象 %s 隐藏段落 %d 的文字被改写' % (sid, pi))
                if not transparent_paragraph(after):
                    errors.append('对象 %s 的段落 %d 应隐藏但未透明占位' % (sid, pi))
            elif signature(before) != signature(after):
                errors.append('对象 %s 的可见段落 %d 与源文件不同' % (sid, pi))
    for key in output.keys() - source.keys():
        errors.append('出现源文件中不存在的对象 %s' % key[0])
    return errors


def legacy_shapes(archive, slide_part):
    rels_part = posixpath.join(posixpath.dirname(slide_part), '_rels', posixpath.basename(slide_part) + '.rels')
    if rels_part not in archive.namelist():
        return {}
    result = {}
    for relation in ET.fromstring(archive.read(rels_part)):
        if not relation.get('Type', '').endswith('/vmlDrawing'):
            continue
        part = posixpath.normpath(posixpath.join(posixpath.dirname(slide_part), relation.get('Target')))
        for element in ET.fromstring(archive.read(part)).iter():
            if element.tag in (VML + 'shape', VML + 'group') and element.get('id'):
                result[element.get('id')] = signature(element)
    return result


def check_legacy_state(source, source_part, original, output, output_part, actual):
    errors = []
    original_drawing = legacy_shapes(source, source_part)
    actual_drawing = legacy_shapes(output, output_part)
    source_ids = {element.get('spid') for element in original.iter(P + 'oleObj') if element.get('spid')}
    actual_ids = {element.get('spid') for element in actual.iter(P + 'oleObj') if element.get('spid')}
    for sid in source_ids & original_drawing.keys():
        if sid not in actual_ids and sid in actual_drawing:
            errors.append('已隐藏公式 %s 的旧格式绘图仍被引用，会提前显示' % sid)
        elif sid in actual_ids and actual_drawing.get(sid) != original_drawing[sid]:
            errors.append('可见公式 %s 的旧格式绘图丢失或改变' % sid)
    return errors


def check_navigation(source, output, pages_by_source):
    errors = []

    def relations(archive, owner):
        part = relationship_part(owner)
        if part not in archive.namelist():
            return {}
        return {element.get('Id'): element for element in ET.fromstring(archive.read(part))}

    for original_part, output_parts in pages_by_source.items():
        for rid, relation in relations(source, original_part).items():
            if not relation.get('Type', '').endswith('/slide') or relation.get('TargetMode') == 'External':
                continue
            target = resolve_part(original_part, relation.get('Target', ''))
            expected = pages_by_source.get(target, [])
            for output_part in output_parts:
                actual = relations(output, output_part).get(rid)
                actual_target = resolve_part(output_part, actual.get('Target', '')) if actual is not None else None
                if not expected or actual_target != expected[0]:
                    errors.append('页内跳转目标错误：%s (%s)' % (output_part, rid))
    source_pres = ET.fromstring(source.read('ppt/presentation.xml'))
    output_pres = ET.fromstring(output.read('ppt/presentation.xml'))
    source_relations = relations(source, 'ppt/presentation.xml')
    output_relations = relations(output, 'ppt/presentation.xml')
    actual_shows = {show.get('id'): show for show in output_pres.findall(P + 'custShowLst/' + P + 'custShow')}
    for show in source_pres.findall(P + 'custShowLst/' + P + 'custShow'):
        expected = []
        for item in show.findall(P + 'sldLst/' + P + 'sld'):
            relation = source_relations.get(item.get(R + 'id'))
            target = resolve_part('ppt/presentation.xml', relation.get('Target', '')) if relation is not None else None
            expected.extend(pages_by_source.get(target, []))
        actual = []
        output_show = actual_shows.get(show.get('id'))
        if output_show is not None:
            for item in output_show.findall(P + 'sldLst/' + P + 'sld'):
                relation = output_relations.get(item.get(R + 'id'))
                actual.append(resolve_part('ppt/presentation.xml', relation.get('Target', '')) if relation is not None else None)
        if actual != expected or output_show is None or output_show.get('name') != show.get('name'):
            errors.append('自定义放映的页面顺序或目标错误：%s' % show.get('name', show.get('id')))
    return errors


def verify(src, dst, log=print):
    errors = []
    warnings = []
    notices = []
    with zipfile.ZipFile(src) as source, zipfile.ZipFile(dst) as output:
        names = set(output.namelist())
        if len(names) != len(output.namelist()):
            errors.append('ZIP 中存在重复文件名')
        damaged = output.testzip()
        if damaged:
            errors.append('ZIP 校验失败：%s' % damaged)
        for name in sorted(names):
            if not name.endswith(('.xml', '.rels', '.vml')):
                continue
            try:
                data = output.read(name)
                root = ET.fromstring(data)
                prefixes = {prefix for _, (prefix, _) in ET.iterparse(io.BytesIO(data), events=('start-ns',))}
                for choice in root.iter(MC + 'Choice'):
                    for prefix in choice.get('Requires', '').split():
                        if prefix not in prefixes:
                            errors.append('%s 的兼容分支前缀 %s 未声明' % (name, prefix))
            except ET.ParseError as error:
                errors.append('XML 解析失败 %s：%s' % (name, error))
        types = ET.fromstring(output.read('[Content_Types].xml'))
        covered = {entry.get('PartName').lstrip('/') for entry in types.findall('{%s}Override' % CT)}
        defaults = {entry.get('Extension') for entry in types.findall('{%s}Default' % CT)}
        for name in sorted(names):
            if name == '[Content_Types].xml' or name.endswith('/'):
                continue
            if name not in covered and name.rsplit('.', 1)[-1] not in defaults:
                errors.append('缺少 Content-Type：%s' % name)
        for name in sorted(names):
            if not name.endswith('.rels'):
                continue
            root = ET.fromstring(output.read(name))
            for relation in root:
                target = relation.get('Target', '')
                if relation.get('TargetMode') == 'External':
                    continue
                target = posixpath.normpath(posixpath.join(name.split('_rels/')[0], target)).lstrip('/')
                if target not in names:
                    errors.append('关系目标缺失 %s → %s' % (name, target))
        presentation = ET.fromstring(output.read('ppt/presentation.xml'))
        slide_ids = [element.get('id') for element in presentation.find(P + 'sldIdLst')]
        if len(set(slide_ids)) != len(slide_ids):
            errors.append('幻灯片编号重复')
        source_slides = slide_order(source)
        output_slides = slide_order(output)
        size = ET.fromstring(source.read('ppt/presentation.xml')).find(P + 'sldSz')
        slide_size = (int(size.get('cx')), int(size.get('cy')))
        expected_count = 0
        checked = 0
        pages_by_source = {}
        for source_number, name in enumerate(source_slides, 1):
            original = ET.fromstring(source.read(name))
            groups, notes = parse_slide_animation(original)
            warnings.extend('%s：%s' % (name, note) for note in notes)
            previous = None
            start = expected_count
            for step in range(-1, len(groups)):
                output_index = expected_count
                expected_count += 1
                if output_index >= len(output_slides):
                    errors.append('输出缺页：源第%d页、步骤%d' % (source_number, step + 1))
                    continue
                actual = ET.fromstring(output.read(output_slides[output_index]))
                if any(True for _ in actual.iter(P + 'timing')):
                    errors.append('输出第%d页仍有动画' % (output_index + 1))
                if any(True for _ in actual.iter(P + 'transition')):
                    errors.append('输出第%d页仍有切换或自动翻页设置' % (output_index + 1))
                state_errors = check_state(original, actual, groups, step, slide_size)
                state_errors.extend(check_legacy_state(source, name, original, output, output_slides[output_index], actual))
                errors.extend('输出第%d页：%s' % (output_index + 1, error) for error in state_errors)
                current = signature(actual.find(P + 'cSld/' + P + 'spTree'))
                if step >= 0 and current == previous and any(e['cls'] in ('entr', 'exit') or e.get('changes') for e in groups[step]):
                    if not state_errors:
                        notices.append('输出第%d页与前页终态相同：对象状态校验通过，保留该点击步骤' % (output_index + 1))
                    else:
                        errors.append('输出第%d页与前页相同，动画没有产生变化' % (output_index + 1))
                previous = current
                checked += 1
            pages_by_source[name] = output_slides[start:expected_count]
        if expected_count != len(output_slides):
            errors.append('输出页数不符：应为%d，实际%d' % (expected_count, len(output_slides)))
        errors.extend(check_navigation(source, output, pages_by_source))
        for name in source.namelist():
            if name.startswith('ppt/media/') and (name not in names or source.read(name) != output.read(name)):
                errors.append('媒体内容丢失或被修改：%s' % name)
        log('输出页数：%d；已核对动画状态：%d' % (len(output_slides), checked))
        log('检查范围：对象显隐、公式兼容分支、旧格式公式绘图、段落占位、移动缩放、位置、图片、重复页、文件结构')
    for warning in dict.fromkeys(warnings):
        log('未支持效果：' + warning)
    for notice in notices:
        log('提示：' + notice)
    for error in errors[:80]:
        log('错误：' + error)
    log('错误数：%d；本检查不替代实际渲染核对。' % len(errors))
    return errors

