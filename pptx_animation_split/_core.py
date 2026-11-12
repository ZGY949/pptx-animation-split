# -*- coding: utf-8 -*-
"""
PPTX Animation Split — Python conversion engine; see ATTRIBUTION.md
把每一页带动画的 PPTX 拆成一串静态幻灯片：每个"鼠标点击"步骤生成一页。
支持进入、退出及部分强调效果在每次点击结束后的静态状态。
"""
import zipfile, re, io, posixpath
import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

from ._motion import motion_endpoint
from ._interaction import expand_interactions
from ._repetition import repetition

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


class AnimationGroups(list):
    def __init__(self):
        super().__init__()
        self.initial = []
        self.info = []


def all_animation_groups(groups):
    return [getattr(groups, 'initial', [])] + list(groups)


def active_animation_groups(groups, upto):
    active = [getattr(groups, 'initial', [])] + list(groups[:max(0, upto + 1)])
    latest = {event['replay_key']: (group_index, event_index)
              for group_index, effects in enumerate(active) for event_index, event in enumerate(effects)
              if event.get('replay_key') is not None}
    return [[event for event_index, event in enumerate(effects)
             if event.get('replay_key') is None or latest[event['replay_key']] == (group_index, event_index)]
            for group_index, effects in enumerate(active)]


def resolve_part(owner, target):
    return posixpath.normpath(posixpath.join(posixpath.dirname(owner), target)).lstrip('/')


def relationship_part(owner):
    return posixpath.join(posixpath.dirname(owner), '_rels', posixpath.basename(owner) + '.rels')


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
    if effect.get('fill') == 'remove' or effect.get('autoRev') in ('1', 'true'):
        return []
    for behavior in behaviors:
        timing = behavior.find(q('cBhvr') + '/' + q('cTn'))
        if timing is not None and (timing.get('fill') == 'remove' or timing.get('autoRev') in ('1', 'true')):
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
    if effect.get('fill') == 'remove' or effect.get('autoRev') in ('1', 'true') or (
        timing is not None and (timing.get('fill') == 'remove' or timing.get('autoRev') in ('1', 'true'))
    ):
        return []
    if motion.get('origin') != 'layout' or motion.get('rAng', '0') != '0':
        return None
    attributes = [node.text for node in motion.iter(q('attrName'))]
    if attributes not in ([], ['ppt_x', 'ppt_y']):
        return None
    endpoint = motion_endpoint(motion.get('path', ''))
    if endpoint is None:
        return None
    return [{'kind': 'translation', 'x': endpoint[0], 'y': endpoint[1]}]


def has_local_font_sizes(shape):
    for body in shape.iter(P + 'txBody'):
        for paragraph in body.findall(A + 'p'):
            paragraph_properties = paragraph.find(A + 'pPr')
            level = paragraph_properties.get('lvl', '0') if paragraph_properties is not None else '0'
            default = paragraph.find(A + 'pPr/' + A + 'defRPr')
            if default is None or default.get('sz') is None:
                default = body.find(A + 'lstStyle/' + A + 'lvl%spPr/' % (int(level) + 1) + A + 'defRPr')
            for run in paragraph:
                if run.tag not in (A + 'r', A + 'fld'):
                    continue
                props = run.find(A + 'rPr')
                if (props is None or props.get('sz') is None) and (default is None or default.get('sz') is None):
                    return False
    return True


def parse_slide_animation(root, click_order=None):
    return expand_interactions(root, click_order, _parse_linear_animation, AnimationGroups, animation_visibility)


def _parse_linear_animation(root):
    """返回 (groups, notes)
    groups: list of list of dict(effect)"""
    timing = root.find(q('timing'))
    if timing is None:
        if any(True for _ in root.iter(q('timing'))):
            return [], ['兼容分支中的动画时间树尚未支持']
        return [], []
    notes = []
    if len(list(root.iter(q('timing')))) != 1:
        notes.append('同一页的多个动画时间树尚未支持')
    if any(node.get('nodeType') == 'interactiveSeq' for node in timing.iter(q('cTn'))):
        notes.append('对象触发的交互动画不能可靠展开为单一点击序列')
    main = None
    for cTn in timing.iter(q('cTn')):
        if cTn.get('nodeType') == 'mainSeq':
            main = cTn
            break
    if main is None:
        if all(node.tag in {q(tag) for tag in ('timing', 'tnLst', 'par', 'cTn')} and
               (node.tag != q('cTn') or node.get('nodeType') == 'tmRoot') for node in timing.iter()):
            return [], notes
        return [], notes + ['动画时间树缺少可识别的主序列，不能当作无动画页面']
    ch = main.find(q('childTnLst'))
    if ch is None:
        return [], notes + ['主动画序列缺少时间节点列表']
    groups = AnimationGroups()
    covered = set()
    parents = {child: parent for parent in timing.iter() for child in parent}
    shape_parents = {child: parent for parent in root.iter() for child in parent}
    if sum(node.get('nodeType') == 'mainSeq' for node in timing.iter(q('cTn'))) != 1:
        notes.append('存在多个主动画序列，尚未支持')
    if any(main not in sequence.iter() for sequence in timing.iter(q('seq'))):
        notes.append('主序列之外或嵌套的顺序时间节点尚未支持')
    root_id = next((node.get('id') for node in timing.iter(q('cTn')) if node.get('nodeType') == 'tmRoot'), None)
    for node in timing.iter(q('cTn')):
        for condition in node.findall(q('endCondLst') + '/' + q('cond')):
            next_click = condition.get('evt') == 'onNext' and condition.find(q('tgtEl') + '/' + q('sldTgt')) is not None
            reference = condition.find(q('tn'))
            slide_end = condition.get('evt') == 'onEnd' and reference is not None and reference.get('val') == root_id
            looping = node.get('repeatCount') == 'indefinite' or node.get('repeatDur') == 'indefinite'
            if not looping or not (next_click or slide_end):
                notes.append('按条件提前结束的动画尚未支持')
    identifiers = [node.get('id') for node in timing.iter(q('cTn')) if node.get('id')]
    if len(identifiers) != len(set(identifiers)):
        notes.append('动画时间节点 ID 重复，事件依赖不明确')
    for node in timing.iter(q('cTn')):
        if node.get('spd') not in (None, '100000') or node.get('tmFilter') or node.get('evtFilter'):
            notes.append('自定义时间速度或时间筛选尚未支持')
    time_nodes = {node.get('id'): node for node in timing.iter(q('cTn')) if node.get('id')}
    starts = {}
    ends = {}
    pending = set()
    simple_durations = {}
    repeat_values = {}

    def end_time(node):
        if id(node) in ends:
            return ends[id(node)]
        key = ('end', id(node))
        if key in pending:
            notes.append('动画时间依赖存在循环')
            return 0
        pending.add(key)
        duration = node.get('dur')
        if duration is not None and duration.isdecimal():
            simple = int(duration)
        else:
            if duration not in (None, '0'):
                notes.append('事件依赖的动画结束时间不确定')
            child_times = node.find(q('childTnLst'))
            child_nodes = [child for child in child_times.iter(q('cTn'))] if child_times is not None else []
            simple = max([start_time(node)] + [end_time(child) for child in child_nodes]) - start_time(node)
        simple_durations[id(node)] = simple
        try:
            active, cycles, looping = repetition(node, simple)
        except ValueError as error:
            notes.append(str(error))
            active, cycles, looping = simple, 1, False
        repeat_values[id(node)] = (active, cycles, looping)
        result = start_time(node) + active
        pending.remove(key)
        ends[id(node)] = result
        return result

    def start_time(node):
        if id(node) in starts:
            return starts[id(node)]
        key = ('start', id(node))
        if key in pending:
            notes.append('动画时间依赖存在循环')
            return 0
        pending.add(key)
        ancestor = parents.get(node)
        while ancestor is not None and ancestor.tag != q('cTn'):
            ancestor = parents.get(ancestor)
        base = start_time(ancestor) if ancestor is not None else 0
        conditions = node.findall(q('stCondLst') + '/' + q('cond'))
        choices = []
        for condition in conditions:
            delay = condition.get('delay', '0')
            if delay == 'indefinite':
                continue
            if not delay.isdecimal():
                notes.append('无法解释动画延时：%s' % delay)
                continue
            event = condition.get('evt')
            reference = condition.find(q('tn'))
            referenced = time_nodes.get(reference.get('val')) if reference is not None else None
            if event in ('onBegin', 'onEnd') and referenced is not None:
                origin = start_time(referenced) if event == 'onBegin' else end_time(referenced)
                if event == 'onEnd' and repeat_values.get(id(referenced), (0, 1, False))[2]:
                    notes.append('依赖无限循环的结束事件没有确定时间，尚未支持')
            elif event is None:
                origin = base
            else:
                notes.append('无法解释动画的事件触发条件：%s' % event)
                continue
            choices.append(origin + int(delay))
        starts[id(node)] = min(choices) if choices else base
        pending.remove(key)
        return starts[id(node)]
    for par in ch.findall(q('par')):
        c = par.find(q('cTn'))
        if c is None:
            continue
        effs = []
        for ec in c.iter(q('cTn')):
            if 'presetID' not in ec.attrib:
                continue
            covered.add(id(ec))
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
                if any(node.tag in (q('charRg'), q('subSp'), q('oleChartEl')) for node in t.iter()):
                    notes.append('按字符或对象内部元素触发的动画尚未支持')
                if tx is not None and prg is None:
                    notes.append('无法识别动画的文字范围')
            ae = ec.find('.//' + q('animEffect'))
            filt = ae.get('filter', '') if ae is not None else ''
            changes = emphasis_changes(ec) if cls == 'emph' else motion_changes(ec) if cls == 'path' else None
            if prg is not None and any(change['kind'] != 'fontcolor' for change in changes or []):
                changes = None
            targets = {target.get('spid') for target in ec.iter(q('spTgt'))}
            if len(targets) != 1 or not spid:
                notes.append('动画目标不唯一或缺失 (preset %s)' % ec.get('presetID'))
            tree = root.find(q('cSld') + '/' + q('spTree'))
            matches = [element for _, element, sid in shape_elements(tree) if sid == spid] if tree is not None else []
            if not matches:
                notes.append('动画目标对象不存在：%s' % spid)
            if prg is not None and (prg[0] < 0 or prg[1] < prg[0] or any(
                prg[1] >= len(shape.findall(q('txBody') + '/' + A + 'p')) for shape in matches
            )):
                notes.append('动画段落范围超出目标文字范围')
            for node in ec.iter(q('cTn')):
                if cls in ('entr', 'exit') and (node.get('autoRev') in ('1', 'true') or node.get('fill') == 'remove'):
                    notes.append('进入或退出动画在结束后复原，终态尚未支持 (preset %s)' % ec.get('presetID'))
            if changes and any(change['kind'] in ('translation', 'scale') for change in changes):
                if not matches:
                    changes = None
                for shape in matches:
                    if any(change['kind'] == 'scale' for change in changes or []) and shape.tag not in (q('pic'), q('grpSp'), q('sp')):
                        changes = None
                    for change in list(changes or []):
                        if change['kind'] != 'scale' or shape.tag not in (q('grpSp'), q('sp')):
                            continue
                        runs = [run for run in shape.iter() if run.tag in (A + 'r', A + 'fld')]
                        if runs and (change['x'] != change['y'] or not has_local_font_sizes(shape)):
                            changes = None
                        if any(node.tag.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/math}') for node in shape.iter()):
                            changes = None
                        if shape.tag == q('sp'):
                            transform = shape.find(P + 'spPr/' + A + 'xfrm')
                            if transform is None or transform.find(A + 'ext') is None:
                                changes = None
                    if any(change['kind'] == 'translation' for change in changes or []):
                        parent = shape_parents.get(shape)
                        while parent is not None:
                            if parent.tag == q('grpSp'):
                                changes = None
                                break
                            parent = shape_parents.get(parent)
            begin = start_time(ec)
            finish = end_time(ec)
            if cls == 'entr':
                for timed in ec.iter(q('cTn')):
                    _, cycles, _ = repeat_values.get(id(timed), (0, 1, False))
                    if cycles > 1:
                        period = simple_durations[id(timed)] * (2 if timed.get('autoRev') in ('1', 'true') else 1)
                        begin = max(begin, start_time(timed) + period * (cycles - 1))
            offset = 0
            ancestor = parents.get(ec)
            repeated = list(ec.iter(q('cTn')))
            while ancestor is not None:
                if ancestor.tag == q('cTn') and (ancestor.get('repeatCount') is not None or ancestor.get('repeatDur') is not None):
                    end_time(ancestor)
                    _, cycles, looping = repeat_values[id(ancestor)]
                    offset += simple_durations[id(ancestor)] * (cycles - 1)
                    repeated.append(ancestor)
                    if ancestor.get('autoRev') in ('1', 'true'):
                        notes.append('动画容器整体反向播放尚未支持')
                ancestor = parents.get(ancestor)
            looping = any(repeat_values.get(id(node), (0, 1, False))[2] for node in repeated)
            if looping:
                groups.info.append('无限循环动画保留一轮完成后的代表状态；循环播放过程不生成额外页面')
                if any(repeat_values.get(id(node), (0, 1, False))[2] and node.get('fill') == 'remove'
                       and node.get('autoRev') not in ('1', 'true') for node in repeated):
                    notes.append('无限循环结束后复原的效果需要明确停止时机，尚未支持')
            if any(node.get('repeatCount') not in (None, '1000') or node.get('repeatDur') is not None for node in repeated):
                if any(node.get('accumulate') == 'always' for node in ec.iter(q('cBhvr'))):
                    notes.append('逐次累加的重复动画尚未支持')
            effs.append(dict(cls=cls, preset=ec.get('presetID'), sub=ec.get('presetSubtype'),
                             node=ec.get('nodeType'), spid=spid, prg=prg, filter=filt,
                             changes=changes, start=begin + offset, end=finish + offset, order=len(covered), time_id=ec.get('id'), looping=looping))
            if cls not in ('entr', 'exit') and not (cls in ('emph', 'path') and changes is not None):
                notes.append('unsupported class %s (preset %s)' % (cls, ec.get('presetID')))
        if effs:
            if effs[0].get('node') in ('withEffect', 'afterEffect', 'withGroup', 'afterGroup'):
                (groups[-1] if groups else groups.initial).extend(effs)
            else:
                groups.append(effs)
    for node in timing.iter(q('cTn')):
        if 'presetID' in node.attrib and id(node) not in covered:
            notes.append('主序列之外的动画未处理 (preset %s)' % node.get('presetID'))
    for behavior in timing.iter():
        if behavior.tag not in {q(tag) for tag in ('anim', 'animClr', 'animEffect', 'animMotion', 'animRot', 'animScale', 'set', 'cmd', 'audio', 'video')}:
            continue
        ancestor = parents.get(behavior)
        while ancestor is not None and id(ancestor) not in covered:
            ancestor = parents.get(ancestor)
        if ancestor is None:
            notes.append('未归入已识别效果的动画行为：%s' % behavior.tag.rsplit('}', 1)[-1])
    for effects in all_animation_groups(groups):
        for index, left in enumerate(effects):
            for right in effects[index + 1:]:
                if left['spid'] != right['spid']:
                    continue
                same_properties = {change['kind'] for change in left.get('changes') or []} & {change['kind'] for change in right.get('changes') or []}
                loop_visibility = (left.get('looping') or right.get('looping')) and left['cls'] in ('entr', 'exit') and right['cls'] in ('entr', 'exit')
                left_end = float('inf') if left.get('looping') else left['end']
                right_end = float('inf') if right.get('looping') else right['end']
                if (same_properties or loop_visibility) and max(left['start'], right['start']) < min(left_end, right_end):
                    notes.append('同一对象的同一属性有重叠动画，叠加规则尚未验证：%s' % left['spid'])
        effects.sort(key=lambda event: event['start'] if event['cls'] == 'entr' else event['end'])
    return groups, list(dict.fromkeys(notes))


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
    declared = sorted(getattr(groups, 'declared', [effect for effects in all_animation_groups(groups) for effect in effects]),
                      key=lambda effect: effect.get('order', 0))
    for effect in declared:
        if effect['cls'] not in ('entr', 'exit') or not effect['spid']:
            continue
        initial = effect['cls'] == 'exit'
        if effect['prg'] is None:
            whole.setdefault(effect['spid'], initial)
        else:
            states = paragraphs.setdefault(effect['spid'], {})
            for index in range(effect['prg'][0], effect['prg'][1] + 1):
                states.setdefault(index, initial)
    for effects in active_animation_groups(groups, upto):
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


def apply_emphasis(shape, effect, slide_size=None, original_shape=None):
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
                original_transform = None
                if original_shape is not None:
                    original_transform = original_shape.find(P + 'spPr/' + A + 'xfrm')
                    if original_transform is None:
                        original_transform = original_shape.find(P + 'grpSpPr/' + A + 'xfrm')
                    if original_transform is None:
                        original_transform = original_shape.find(P + 'xfrm')
                original_offset = original_transform.find(A + 'off') if original_transform is not None else offset
                original_extent = original_transform.find(A + 'ext') if original_transform is not None else extent
                for axis, dimension, slide_dimension in (('x', 'cx', slide_size[0]), ('y', 'cy', slide_size[1])):
                    center = int(original_offset.get(axis)) + int(original_extent.get(dimension)) / 2
                    offset.set(axis, str(round(center + change[axis] * slide_dimension - int(extent.get(dimension)) / 2)))
            else:
                for coordinate, dimension in (('x', 'cx'), ('y', 'cy')):
                    before = int(extent.get(dimension))
                    after = round(before * change[coordinate] / 100000)
                    offset.set(coordinate, str(int(offset.get(coordinate)) + round((before - after) / 2)))
                    extent.set(dimension, str(after))
                if shape.tag in (q('grpSp'), q('sp')):
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
    parents = {child: parent for parent in root.iter() for child in parent}
    for timing in list(root.iter(q('timing'))):
        parents[timing].remove(timing)
    for transition in list(root.iter(q('transition'))):
        parents[transition].remove(transition)
    for alternate in reversed(list(root.iter(MC + 'AlternateContent'))):
        if all(len(branch) == 0 for branch in alternate):
            parents[alternate].remove(alternate)
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

    reference_shapes = {id(element): copy.deepcopy(element) for _, element, _ in shape_elements(spTree)}
    for effects in active_animation_groups(groups, upto):
        for effect in effects:
            if effect['cls'] in ('emph', 'path') and effect.get('changes'):
                for _, el, sid in shape_elements(spTree):
                    if sid == effect['spid']:
                        apply_emphasis(el, effect, slide_size, reference_shapes[id(el)])

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
    data = ET.tostring(root, encoding='UTF-8').replace(b'\r', b'&#13;')
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


def split_pptx(src, dst, log=print, click_orders=None):
    with zipfile.ZipFile(src) as archive:
        return _split_archive(archive, dst, log, click_orders or {})


def _split_archive(z, dst, log, click_orders=None):
    click_orders = click_orders or {}
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
        if rel.get('Type', '').endswith('/slide') and rel.get('TargetMode') != 'External':
            old_slide_rels[rel.get('Id')] = resolve_part('ppt/presentation.xml', rel.get('Target', ''))

    plan = []          # (src_slide_name, step_index)
    per_slide = []
    all_notes = []
    for s in src_slides:
        root = ET.fromstring(z.read(s))
        groups, notes = parse_slide_animation(root, click_orders.get(s))
        for information in dict.fromkeys(getattr(groups, 'info', [])):
            log('%s：%s' % (s, information))
        cSld = root.find(q('cSld'))
        tree = cSld.find(q('spTree')) if cSld is not None else None
        shapes = list(shape_elements(tree)) if tree is not None else []
        for effects in all_animation_groups(groups):
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
    for e in list(sldIdLst):
        sldIdLst.remove(e)

    new_pres_entries = []
    first_idx_by_src = {}
    refs_by_source = {}
    for idx, (source_part, _) in enumerate(plan, 1):
        first_idx_by_src.setdefault(source_part, idx)
        refs_by_source.setdefault(source_part, []).append('rId%d' % (max_rel + idx))
    ct_add = []
    for idx, (s, k) in enumerate(plan, start=1):
        new_name = 'ppt/slides/slide%d.xml' % idx
        source_root = ET.fromstring(z.read(s))
        groups, _ = parse_slide_animation(source_root, click_orders.get(s))
        root = clone_and_render(z.read(s), groups, k, slide_size)
        new_slides[new_name] = serialize(root, collect_ns(z.read(s)))

        first_idx = first_idx_by_src[s]

        # rels（备注页只保留在该源页的第一张拆分结果上）
        rels_name = relationship_part(s)
        if rels_name in names:
            rl = ET.fromstring(z.read(rels_name))
            if idx != first_idx:
                for rel in list(rl):
                    if rel.get('Type', '').endswith('/notesSlide'):
                        rl.remove(rel)
            copies = filter_legacy_drawings(z, s, source_root, root, idx, rl, new_slides)
            for original_part, new_part in copies:
                if '/' + original_part in ct_map:
                    ct_add.append(('/' + new_part, ct_map['/' + original_part]))
            for relation in rl:
                if relation.get('TargetMode') == 'External':
                    continue
                target = resolve_part(s, relation.get('Target', ''))
                if relation.get('Type', '').endswith('/slide'):
                    if target not in first_idx_by_src:
                        raise ValueError('页内链接指向主放映顺序之外的幻灯片：%s' % target)
                    target = 'ppt/slides/slide%d.xml' % first_idx_by_src[target]
                relation.set('Target', posixpath.relpath(target, posixpath.dirname(new_name)))
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

    # 重建 sldIdLst
    for rid, nid in new_pres_entries:
        e = ET.SubElement(sldIdLst, q('sldId'))
        e.set('id', nid)
        e.set(R + 'id', rid)

    # 自定义放映：把每张原幻灯片替换为拆分后的多张
    cust = pres.find(q('custShowLst'))
    if cust is not None:
        for show in cust.findall(q('custShow')):
            sl = show.find(q('sldLst'))
            if sl is None:
                raise ValueError('自定义放映缺少可识别的幻灯片列表')
            new_refs = []
            for e in sl.findall(q('sld')):
                source_part = old_slide_rels.get(e.get(R + 'id'))
                if source_part not in refs_by_source:
                    raise ValueError('自定义放映引用了主放映顺序之外的幻灯片')
                new_refs.extend(refs_by_source[source_part])
            for e in list(sl):
                sl.remove(e)
            for ref in new_refs:
                ET.SubElement(sl, q('sld'), {R + 'id': ref})
        log('已更新自定义放映中的幻灯片引用')
    for relation in list(pres_rels):
        if relation.get('Id') in old_slide_rels and old_slide_rels[relation.get('Id')] in first_idx_by_src:
            pres_rels.remove(relation)

    # 节（section list）无法可靠重映射：移除
    extLst = pres.find(q('extLst'))
    if extLst is not None:
        pres.remove(extLst)
        log('已移除 presentation extLst（分节信息），避免编号错乱')

    # content types
    for ov in list(ctypes):
        pn = ov.get('PartName', '')
        if pn.lstrip('/') in src_slides:
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
            if not rel.get('Type', '').endswith('/slide') or rel.get('TargetMode') == 'External':
                continue
            owner = n.replace('/_rels/', '/').removesuffix('.rels')
            target = resolve_part(owner, rel.get('Target', ''))
            if target in first_idx_by_src:
                new_target = 'ppt/slides/slide%d.xml' % first_idx_by_src[target]
                rel.set('Target', posixpath.relpath(new_target, posixpath.dirname(owner)))
                changed = True
        if changed:
            new_slides[n] = serialize(rl)

    # 写回
    skip = set(src_slides) | {relationship_part(part) for part in src_slides}
    for n in names:
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

