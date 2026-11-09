# -*- coding: utf-8 -*-
"""
PPTX Animation Split — Python conversion engine; see ATTRIBUTION.md
把每一页带动画的 PPTX 拆成一串静态幻灯片：每个"鼠标点击"步骤生成一页。
支持进入、退出及部分强调效果在每次点击结束后的静态状态。
"""
import zipfile, re, io, posixpath
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
PR = 'http://schemas.openxmlformats.org/package/2006/relationships'
OD = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PML = 'http://schemas.openxmlformats.org/presentationml/2006/main'
DML = 'http://schemas.openxmlformats.org/drawingml/2006/main'

P = '{%s}' % PML
A = '{%s}' % DML
R = '{%s}' % OD
MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
VML = '{urn:schemas-microsoft-com:vml}'


def collect_ns(data):
    out = {}
    for ev, (prefix, uri) in ET.iterparse(io.BytesIO(data), events=('start-ns',)):
        out[prefix] = uri
    return out


def register_all(z):
    for n in z.namelist():
        if n.endswith('.xml') or n.endswith('.rels'):
            try:
                for prefix, uri in collect_ns(z.read(n)).items():
                    try:
                        ET.register_namespace(prefix, uri)
                    except (ValueError, KeyError):
                        pass
            except ET.ParseError:
                pass


def q(tag):
    return P + tag


SHAPE_TAGS = ('sp', 'pic', 'cxnSp', 'graphicFrame', 'grpSp')
NV_TAGS = ('nvSpPr', 'nvPicPr', 'nvCxnSpPr', 'nvGraphicFramePr', 'nvGrpSpPr')


def shape_elements(container):
    """递归 yield (parent, element, shape_id)"""
    for el in list(container):
        if el.tag in (MC + 'AlternateContent', MC + 'Choice', MC + 'Fallback'):
            yield from shape_elements(el)
            continue
        if el.tag not in [q(t) for t in SHAPE_TAGS]:
            continue
        sid = None
        for t in NV_TAGS:
            nv = el.find(q(t))
            if nv is not None:
                cnv = nv.find(q('cNvPr'))
                if cnv is not None:
                    sid = cnv.get('id')
                break
        if sid:
            yield container, el, sid
        if el.tag == q('grpSp'):
            for r in shape_elements(el):
                yield r


def emphasis_changes(effect):
    changes = []
    behaviors = effect.find(q('childTnLst'))
    if behaviors is None:
        return None
    if effect.get('fill') == 'remove' or effect.get('autoRev') == '1':
        return []
    for behavior in behaviors:
        timing = behavior.find(q('cBhvr') + '/' + q('cTn'))
        if timing is not None and (timing.get('fill') == 'remove' or timing.get('autoRev') == '1'):
            continue
        if effect.get('fill') == 'remove':
            continue
        if behavior.tag == q('animClr'):
            attributes = [node.text for node in behavior.iter(q('attrName'))]
            to = behavior.find(q('to'))
            if attributes != ['style.color'] or to is None or len(to) != 1:
                return None
            changes.append({'kind': 'fontcolor', 'color': ET.tostring(to[0], encoding='unicode')})
        elif behavior.tag == q('animRot') and behavior.get('by') is not None:
            changes.append({'kind': 'rotation', 'by': int(behavior.get('by'))})
        elif behavior.tag == q('animScale'):
            by = behavior.find(q('by'))
            if by is None or behavior.find(q('from')) is not None or behavior.find(q('to')) is not None:
                return None
            try:
                x, y = int(by.get('x')), int(by.get('y'))
            except (TypeError, ValueError):
                return None
            if x <= 0 or y <= 0:
                return None
            changes.append({'kind': 'scale', 'x': x, 'y': y})
        else:
            return None
    return changes


def motion_changes(effect):
    behaviors = effect.find(q('childTnLst'))
    if behaviors is None or len(behaviors) != 1 or behaviors[0].tag != q('animMotion'):
        return None
    motion = behaviors[0]
    timing = motion.find(q('cBhvr') + '/' + q('cTn'))
    if effect.get('fill') == 'remove' or effect.get('autoRev') == '1' or (
        timing is not None and (timing.get('fill') == 'remove' or timing.get('autoRev') == '1')
    ):
        return []
    if motion.get('origin') != 'layout' or motion.get('rAng', '0') != '0':
        return None
    attributes = [node.text for node in motion.iter(q('attrName'))]
    if attributes not in ([], ['ppt_x', 'ppt_y']):
        return None
    number = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
    match = re.fullmatch(r'\s*M\s*(' + number + r')\s+(' + number +
                         r')\s+L\s*(' + number + r')\s+(' + number + r')\s*(?:E\s*)?',
                         motion.get('path', ''))
    if match is None:
        return None
    return [{'kind': 'translation', 'x': float(match.group(3)), 'y': float(match.group(4))}]


def parse_slide_animation(root):
    """返回 (groups, notes)
    groups: list of list of dict(effect)"""
    timing = root.find(q('timing'))
    if timing is None:
        return [], []
    main = None
    for cTn in timing.iter(q('cTn')):
        if cTn.get('nodeType') == 'mainSeq':
            main = cTn
            break
    if main is None:
        return [], []
    ch = main.find(q('childTnLst'))
    if ch is None:
        return [], []
    groups = []
    notes = []
    motion_targets = set()
    for par in ch.findall(q('par')):
        c = par.find(q('cTn'))
        if c is None:
            continue
        effs = []
        for ec in c.iter(q('cTn')):
            if 'presetID' not in ec.attrib:
                continue
            cls = ec.get('presetClass')
            tgt = None
            spid = None
            prg = None
            t = ec.find('.//' + q('spTgt'))
            if t is not None:
                spid = t.get('spid')
                tx = t.find(q('txEl'))
                if tx is not None:
                    r = tx.find(q('pRg'))
                    if r is not None:
                        try:
                            prg = (int(r.get('st', 0)), int(r.get('end', 0)))
                        except ValueError:
                            prg = None
            ae = ec.find('.//' + q('animEffect'))
            filt = ae.get('filter', '') if ae is not None else ''
            changes = emphasis_changes(ec) if cls == 'emph' else motion_changes(ec) if cls == 'path' else None
            if changes and any(change['kind'] in ('translation', 'scale') for change in changes):
                tree = root.find(q('cSld') + '/' + q('spTree'))
                matches = [element for _, element, sid in shape_elements(tree) if sid == spid] if tree is not None else []
                parents = {child: parent for parent in root.iter() for child in parent}
                if not matches:
                    changes = None
                for shape in matches:
                    if any(change['kind'] == 'scale' for change in changes or []) and shape.tag not in (q('pic'), q('grpSp')):
                        changes = None
                    for change in list(changes or []):
                        if change['kind'] != 'scale' or shape.tag != q('grpSp'):
                            continue
                        runs = [run for run in shape.iter() if run.tag in (A + 'r', A + 'fld')]
                        if runs and (change['x'] != change['y'] or any(
                            run.find(A + 'rPr') is None or run.find(A + 'rPr').get('sz') is None for run in runs
                        )):
                            changes = None
                    if any(change['kind'] == 'translation' for change in changes or []):
                        parent = parents.get(shape)
                        while parent is not None:
                            if parent.tag == q('grpSp'):
                                changes = None
                                break
                            parent = parents.get(parent)
                if changes and cls == 'path':
                    if spid in motion_targets:
                        changes = None
                    else:
                        motion_targets.add(spid)
            effs.append(dict(cls=cls, preset=ec.get('presetID'), sub=ec.get('presetSubtype'),
                             node=ec.get('nodeType'), spid=spid, prg=prg, filter=filt,
                             changes=changes))
            if cls not in ('entr', 'exit') and not (cls in ('emph', 'path') and changes is not None):
                notes.append('unsupported class %s (preset %s)' % (cls, ec.get('presetID')))
        if effs:
            groups.append(effs)
    return groups, notes


def hide_paragraph(paragraph):
    ppr = paragraph.find(A + 'pPr')
    if ppr is None:
        ppr = ET.Element(A + 'pPr')
        paragraph.insert(0, ppr)
    if ppr.find(A + 'defRPr') is None:
        ET.SubElement(ppr, A + 'defRPr')
    if paragraph.find(A + 'endParaRPr') is None:
        ET.SubElement(paragraph, A + 'endParaRPr')
    for run in list(paragraph.iter()):
        if run.tag in (A + 'r', A + 'fld', A + 'br') and run.find(A + 'rPr') is None:
            run.insert(0, ET.Element(A + 'rPr'))
    fill_tags = {A + t for t in ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill', 'highlight', 'uFill', 'effectLst', 'effectDag')}
    for props in list(paragraph.iter()):
        if props.tag not in (A + 'rPr', A + 'defRPr', A + 'endParaRPr'):
            continue
        for child in list(props):
            if child.tag in fill_tags:
                props.remove(child)
        line = props.find(A + 'ln')
        if line is not None:
            for child in list(line):
                if child.tag in fill_tags:
                    line.remove(child)
            line.insert(0, ET.Element(A + 'noFill'))
        fill = ET.Element(A + 'solidFill')
        color = ET.SubElement(fill, A + 'srgbClr', val='000000')
        ET.SubElement(color, A + 'alpha', val='0')
        props.insert(1 if line is not None else 0, fill)


def slide_order(z):
    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
    relmap = {r.get('Id'): r.get('Target') for r in rels}
    return [posixpath.normpath(posixpath.join('ppt', relmap[e.get(R + 'id')])).lstrip('/')
            for e in pres.find(q('sldIdLst'))]


def animation_visibility(groups, upto):
    whole = {}
    paragraphs = {}
    for effects in groups:
        for effect in effects:
            if effect['cls'] not in ('entr', 'exit') or not effect['spid']:
                continue
            initial = effect['cls'] == 'exit'
            if effect['prg'] is None:
                whole.setdefault(effect['spid'], initial)
            else:
                states = paragraphs.setdefault(effect['spid'], {})
                for index in range(effect['prg'][0], effect['prg'][1] + 1):
                    states.setdefault(index, initial)
    for effects in groups[:upto + 1]:
        for effect in effects:
            if effect['cls'] not in ('entr', 'exit') or not effect['spid']:
                continue
            visible = effect['cls'] == 'entr'
            if effect['prg'] is None:
                whole[effect['spid']] = visible
            else:
                for index in range(effect['prg'][0], effect['prg'][1] + 1):
                    paragraphs[effect['spid']][index] = visible
    return {sid for sid, visible in whole.items() if not visible}, {
        sid: {index for index, visible in states.items() if not visible}
        for sid, states in paragraphs.items()}


def scale_group_text(shape, factor):
    for body in shape.iter(P + 'txBody'):
        props = body.find(A + 'bodyPr')
        if props is not None:
            for name, default in (('lIns', 91440), ('rIns', 91440), ('tIns', 45720), ('bIns', 45720)):
                props.set(name, str(round(int(props.get(name, default)) * factor)))
        for node in body.iter():
            if node.tag in (A + 'rPr', A + 'defRPr', A + 'endParaRPr'):
                for name in ('sz', 'spc', 'kern'):
                    if node.get(name) is not None:
                        node.set(name, str(round(int(node.get(name)) * factor)))
            elif node.tag == A + 'pPr':
                for name in ('marL', 'marR', 'indent', 'defTabSz'):
                    if node.get(name) is not None:
                        node.set(name, str(round(int(node.get(name)) * factor)))
            elif node.tag == A + 'spcPts' and node.get('val') is not None:
                node.set('val', str(round(int(node.get('val')) * factor)))
            elif node.tag == A + 'tab' and node.get('pos') is not None:
                node.set('pos', str(round(int(node.get('pos')) * factor)))


def apply_emphasis(shape, effect, slide_size=None):
    for change in effect.get('changes') or []:
        if change['kind'] in ('rotation', 'translation', 'scale'):
            transform = shape.find(P + 'spPr/' + A + 'xfrm')
            if transform is None:
                transform = shape.find(P + 'grpSpPr/' + A + 'xfrm')
            if transform is None:
                transform = shape.find(P + 'xfrm')
            if transform is None:
                raise ValueError('动画对象缺少坐标信息')
            if change['kind'] == 'rotation':
                transform.set('rot', str((int(transform.get('rot', '0')) + change['by']) % 21600000))
                continue
            offset = transform.find(A + 'off')
            extent = transform.find(A + 'ext')
            if offset is None or extent is None:
                raise ValueError('移动或缩放对象缺少位置和尺寸')
            if change['kind'] == 'translation':
                if slide_size is None:
                    raise ValueError('移动动画缺少幻灯片尺寸')
                offset.set('x', str(int(offset.get('x')) + round(change['x'] * slide_size[0])))
                offset.set('y', str(int(offset.get('y')) + round(change['y'] * slide_size[1])))
            else:
                for coordinate, dimension in (('x', 'cx'), ('y', 'cy')):
                    before = int(extent.get(dimension))
                    after = round(before * change[coordinate] / 100000)
                    offset.set(coordinate, str(int(offset.get(coordinate)) + round((before - after) / 2)))
                    extent.set(dimension, str(after))
                if shape.tag == q('grpSp'):
                    scale_group_text(shape, change['x'] / 100000)
        elif change['kind'] == 'fontcolor':
            body = shape.find(P + 'txBody')
            if body is None:
                raise ValueError('文字变色对象缺少文本框')
            paragraphs = body.findall(A + 'p')
            span = effect.get('prg')
            for index, paragraph in enumerate(paragraphs):
                if span is not None and not span[0] <= index <= span[1]:
                    continue
                for run in list(paragraph.iter()):
                    if run.tag in (A + 'r', A + 'fld', A + 'br') and run.find(A + 'rPr') is None:
                        run.insert(0, ET.Element(A + 'rPr'))
                for props in list(paragraph.iter()):
                    if props.tag not in (A + 'rPr', A + 'defRPr', A + 'endParaRPr'):
                        continue
                    for child in list(props):
                        if child.tag in {A + tag for tag in ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill')}:
                            props.remove(child)
                    fill = ET.Element(A + 'solidFill')
                    fill.append(ET.fromstring(change['color']))
                    props.insert(1 if props.find(A + 'ln') is not None else 0, fill)


def clone_and_render(xml_bytes, groups, upto, slide_size=None):
    """生成第 upto 个点击步骤之后的状态（upto=-1 表示初始状态）"""
    root = ET.fromstring(xml_bytes)
    t = root.find(q('timing'))
    if t is not None:
        root.remove(t)
    cSld = root.find(q('cSld'))
    spTree = cSld.find(q('spTree')) if cSld is not None else None
    if spTree is None:
        return root

    hidden_shapes, hidden_paragraphs = animation_visibility(groups, upto)
    for parent, el, sid in list(shape_elements(spTree)):
        if sid in hidden_shapes:
            parent.remove(el)

    parents = {child: parent for parent in spTree.iter() for child in parent}
    for el in reversed(list(spTree.iter(MC + 'AlternateContent'))):
        if not any(child.tag in {q(t) for t in SHAPE_TAGS} for child in el.iter()):
            parents[el].remove(el)

    for effects in groups[:upto + 1]:
        for effect in effects:
            if effect['cls'] in ('emph', 'path') and effect.get('changes'):
                for _, el, sid in shape_elements(spTree):
                    if sid == effect['spid']:
                        apply_emphasis(el, effect, slide_size)

    for sid, hidden in hidden_paragraphs.items():
        for parent, el, csid in list(shape_elements(spTree)):
            if csid != sid:
                continue
            body = el.find(q('txBody'))
            if body is None:
                continue
            paras = body.findall(A + 'p')
            for idx, p in enumerate(paras):
                if idx in hidden:
                    hide_paragraph(p)
    return root


def serialize(root, namespaces=None):
    namespaces = namespaces or {}
    for prefix, uri in namespaces.items():
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass
    data = ET.tostring(root, encoding='UTF-8')
    declared = {prefix for prefix, _ in collect_ns(data).items()}
    required = set()
    for element in root.iter():
        for name, value in element.attrib.items():
            if (element.tag == MC + 'Choice' and name == 'Requires') or name in {
                MC + item for item in ('Ignorable', 'MustUnderstand', 'ProcessContent', 'PreserveElements', 'PreserveAttributes')
            }:
                required.update(token.split(':')[0] for token in value.split())
    declarations = []
    for prefix in sorted(required - declared - {'xml'}):
        if prefix not in namespaces:
            raise ValueError('兼容内容缺少命名空间声明：%s' % prefix)
        declarations.append(('xmlns:%s=%s' % (prefix, quoteattr(namespaces[prefix]))).encode('utf-8'))
    if declarations:
        boundary = data.index(b'>')
        if data[boundary - 1:boundary] == b'/':
            boundary -= 1
        data = data[:boundary] + b' ' + b' '.join(declarations) + data[boundary:]
    if not data.startswith(b'<'):
        data = data.split(b'>', 1)[1]
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n' + data


def filter_legacy_drawings(source, source_part, source_root, rendered_root, slide_number, relationships, resources):
    source_objects = {element.get('spid') for element in source_root.iter(P + 'oleObj') if element.get('spid')}
    visible_objects = {element.get('spid') for element in rendered_root.iter(P + 'oleObj') if element.get('spid')}
    hidden_objects = source_objects - visible_objects
    original_ids = {element.get(R + 'id') for element in source_root.iter(P + 'oleObj')}
    visible_ids = {element.get(R + 'id') for element in rendered_root.iter(P + 'oleObj')}
    copies = []
    for index, relation in enumerate(list(relationships)):
        kind = relation.get('Type', '')
        if kind.endswith('/oleObject') and relation.get('Id') in original_ids - visible_ids:
            relationships.remove(relation)
            continue
        if not hidden_objects or not kind.endswith('/vmlDrawing'):
            continue
        original_part = posixpath.normpath(posixpath.join(posixpath.dirname(source_part), relation.get('Target')))
        data = source.read(original_part)
        drawing = ET.fromstring(data)
        parents = {child: parent for parent in drawing.iter() for child in parent}
        changed = False
        for element in list(drawing.iter()):
            if element.get('id') in hidden_objects and element in parents:
                parents[element].remove(element)
                changed = True
        if not changed:
            continue
        if not any(element.tag in (VML + 'shape', VML + 'group') for element in drawing.iter()):
            relationships.remove(relation)
            continue
        new_part = posixpath.join(posixpath.dirname(original_part), 'vmlDrawing_split_%d_%d.vml' % (slide_number, index))
        resources[new_part] = serialize(drawing, collect_ns(data))
        relation.set('Target', posixpath.relpath(new_part, posixpath.dirname(source_part)))
        original_rels = posixpath.join(posixpath.dirname(original_part), '_rels', posixpath.basename(original_part) + '.rels')
        if original_rels in source.namelist():
            new_rels = posixpath.join(posixpath.dirname(new_part), '_rels', posixpath.basename(new_part) + '.rels')
            resources[new_rels] = source.read(original_rels)
        copies.append((original_part, new_part))
    return copies


def split_pptx(src, dst, log=print):
    with zipfile.ZipFile(src) as archive:
        return _split_archive(archive, dst, log)


def _split_archive(z, dst, log):
    register_all(z)
    names = z.namelist()
    src_slides = slide_order(z)

    pres = ET.fromstring(z.read('ppt/presentation.xml'))
    size = pres.find(q('sldSz'))
    slide_size = (int(size.get('cx')), int(size.get('cy')))
    pres_rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
    ctypes = ET.fromstring(z.read('[Content_Types].xml'))

    ct_map = {}
    for ov in ctypes.findall('{%s}Override' % CT):
        ct_map[ov.get('PartName')] = ov.get('ContentType')

    # presentation.rels 中原始 slide 的 rid
    old_slide_rels = {}
    for rel in list(pres_rels):
        t = rel.get('Target', '')
        if re.match(r'slides/slide\d+\.xml$', t):
            old_slide_rels[rel.get('Id')] = t

    plan = []          # (src_slide_name, step_index)
    per_slide = []
    all_notes = []
    for s in src_slides:
        root = ET.fromstring(z.read(s))
        groups, notes = parse_slide_animation(root)
        cSld = root.find(q('cSld'))
        tree = cSld.find(q('spTree')) if cSld is not None else None
        shapes = list(shape_elements(tree)) if tree is not None else []
        for effects in groups:
            for effect in effects:
                if effect['cls'] not in ('entr', 'exit') and not effect.get('changes'):
                    continue
                matches = [el for _, el, sid in shapes if sid == effect['spid']]
                if not matches:
                    raise ValueError('%s: 找不到进入动画目标 %s' % (s, effect['spid']))
                if effect['prg'] is not None:
                    end = effect['prg'][1]
                    for el in matches:
                        body = el.find(q('txBody'))
                        if body is None or end >= len(body.findall(A + 'p')):
                            raise ValueError('%s: 无法保留段落动画目标 %s 的排版' % (s, effect['spid']))
        all_notes += [(s, n) for n in notes]
        nsteps = len(groups)
        for k in range(-1, nsteps):
            plan.append((s, k))
        per_slide.append((s, nsteps + 1, nsteps))

    log('输出页数: %d (原 %d 页)' % (len(plan), len(src_slides)))

    # 全新 slide 编号
    new_slides = {}
    max_rel = 0
    for rel in pres_rels:
        m = re.match(r'rId(\d+)$', rel.get('Id', ''))
        if m:
            max_rel = max(max_rel, int(m.group(1)))

    used_ids = set()
    sldIdLst = pres.find(q('sldIdLst'))
    if sldIdLst is None:
        sldIdLst = ET.SubElement(pres, q('sldIdLst'))
    # 记录原 sldId -> 源幻灯片编号（用于自定义放映重映射）
    old_sldid_to_srcnum = {}
    for e in list(sldIdLst):
        rid = e.get(R + 'id')
        tgt = old_slide_rels.get(rid, '')
        m = re.search(r'slide(\d+)\.xml', tgt)
        if m:
            old_sldid_to_srcnum[e.get('id')] = m.group(1)
        sldIdLst.remove(e)

    new_pres_entries = []
    srcnum_to_newids = {}
    first_idx_by_src = {}
    ct_add = []
    for idx, (s, k) in enumerate(plan, start=1):
        new_name = 'ppt/slides/slide%d.xml' % idx
        source_root = ET.fromstring(z.read(s))
        groups, _ = parse_slide_animation(source_root)
        root = clone_and_render(z.read(s), groups, k, slide_size)
        new_slides[new_name] = serialize(root, collect_ns(z.read(s)))

        srcnum_here = re.search(r'slide(\d+)\.xml', s).group(1)
        first_idx = first_idx_by_src.setdefault(srcnum_here, idx)

        # rels（备注页只保留在该源页的第一张拆分结果上）
        rels_name = 'ppt/slides/_rels/slide%s.xml.rels' % srcnum_here
        if rels_name in names:
            rl = ET.fromstring(z.read(rels_name))
            if idx != first_idx:
                for rel in list(rl):
                    if 'notesSlide' in rel.get('Target', ''):
                        rl.remove(rel)
            copies = filter_legacy_drawings(z, s, source_root, root, idx, rl, new_slides)
            for original_part, new_part in copies:
                if '/' + original_part in ct_map:
                    ct_add.append(('/' + new_part, ct_map['/' + original_part]))
            new_slides['ppt/slides/_rels/slide%d.xml.rels' % idx] = serialize(rl, collect_ns(z.read(rels_name)))

        # content type
        src_part = '/' + s
        if src_part in ct_map:
            ct_add.append(('/' + new_name, ct_map[src_part]))

        # rel
        max_rel += 1
        rid = 'rId%d' % max_rel
        rel = ET.Element('{%s}Relationship' % PR)
        rel.set('Id', rid)
        rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide')
        rel.set('Target', 'slides/slide%d.xml' % idx)
        pres_rels.append(rel)

        new_id = 256 + idx
        while new_id in used_ids:
            new_id += 1
        used_ids.add(new_id)
        new_pres_entries.append((rid, str(new_id)))
        srcnum = re.search(r'slide(\d+)\.xml', s).group(1)
        srcnum_to_newids.setdefault(srcnum, []).append(str(new_id))

    # 重建 sldIdLst
    for rid, nid in new_pres_entries:
        e = ET.SubElement(sldIdLst, q('sldId'))
        e.set('id', nid)
        e.set(R + 'id', rid)

    # 自定义放映：把每张原幻灯片替换为拆分后的多张
    cust = pres.find(q('custShowLst'))
    if cust is not None:
        for show in cust.findall(q('custShow')):
            sl = show.find(q('sldIdLst'))
            if sl is None:
                continue
            new_ids = []
            for e in sl.findall(q('sldId')):
                srcnum = old_sldid_to_srcnum.get(e.get('id'))
                new_ids += srcnum_to_newids.get(srcnum, [e.get('id')])
            for e in list(sl.findall(q('sldId'))):
                sl.remove(e)
            for nid in new_ids:
                ne = ET.SubElement(sl, q('sldId'))
                ne.set('id', nid)
        log('已更新自定义放映中的幻灯片引用')

    # 节（section list）无法可靠重映射：移除
    extLst = pres.find(q('extLst'))
    if extLst is not None:
        pres.remove(extLst)
        log('已移除 presentation extLst（分节信息），避免编号错乱')

    # content types
    for ov in list(ctypes):
        pn = ov.get('PartName', '')
        if re.match(r'/ppt/slides/slide\d+\.xml$', pn):
            ctypes.remove(ov)
    for pn, c in ct_add:
        ov = ET.SubElement(ctypes, '{%s}Override' % CT)
        ov.set('PartName', pn)
        ov.set('ContentType', c)

    default_types = {el.get('Extension').lower(): el.get('ContentType')
                     for el in ctypes.findall('{%s}Default' % CT)}
    exact_extensions = {el.get('Extension') for el in ctypes.findall('{%s}Default' % CT)}
    for name in names:
        extension = name.rsplit('.', 1)[-1]
        if extension not in exact_extensions and extension.lower() in default_types:
            ET.SubElement(ctypes, '{%s}Default' % CT, Extension=extension,
                          ContentType=default_types[extension.lower()])
            exact_extensions.add(extension)

    # 备注页关系：改为指向该源页拆分后的第一张
    for n in names:
        if not re.match(r'ppt/notesSlides/_rels/notesSlide\d+\.xml\.rels$', n):
            continue
        rl = ET.fromstring(z.read(n))
        changed = False
        for rel in rl:
            m = re.search(r'slides/slide(\d+)\.xml', rel.get('Target', ''))
            if m and m.group(1) in first_idx_by_src:
                rel.set('Target', '../slides/slide%d.xml' % first_idx_by_src[m.group(1)])
                changed = True
        if changed:
            new_slides[n] = serialize(rl)

    # 写回
    skip = set()
    for n in names:
        if re.match(r'ppt/slides/slide\d+\.xml$', n) or re.match(r'ppt/slides/_rels/slide\d+\.xml\.rels$', n):
            skip.add(n)
        if n in new_slides:
            skip.add(n)
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as out:
        for n in names:
            if n in skip or n in ('ppt/presentation.xml', 'ppt/_rels/presentation.xml.rels', '[Content_Types].xml'):
                continue
            out.writestr(n, z.read(n))
        for n in sorted(new_slides, key=lambda x: (x.count('/'), x)):
            out.writestr(n, new_slides[n])
        out.writestr('ppt/presentation.xml', serialize(pres, collect_ns(z.read('ppt/presentation.xml'))))
        out.writestr('ppt/_rels/presentation.xml.rels', serialize(pres_rels, collect_ns(z.read('ppt/_rels/presentation.xml.rels'))))
        out.writestr('[Content_Types].xml', serialize(ctypes, collect_ns(z.read('[Content_Types].xml'))))

    return per_slide, all_notes, len(plan)

