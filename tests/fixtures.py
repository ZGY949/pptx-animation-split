import base64
import copy
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
import zipfile


P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PR = '{http://schemas.openxmlformats.org/package/2006/relationships}'
CT = '{http://schemas.openxmlformats.org/package/2006/content-types}'
OD = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
DEMO = Path(__file__).resolve().parents[1] / 'examples/demo.pptx'
PIXEL = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


def shape(sid, kind='text'):
    tag = 'pic' if kind == 'picture' else 'grpSp' if kind == 'group' else 'sp'
    root = ET.Element(P + tag)
    nv = ET.SubElement(root, P + ('nvPicPr' if kind == 'picture' else 'nvGrpSpPr' if kind == 'group' else 'nvSpPr'))
    ET.SubElement(nv, P + 'cNvPr', id=str(sid), name=kind + '_' + str(sid))
    ET.SubElement(nv, P + ('cNvPicPr' if kind == 'picture' else 'cNvGrpSpPr' if kind == 'group' else 'cNvSpPr'))
    ET.SubElement(nv, P + 'nvPr')
    if kind == 'picture':
        fill = ET.SubElement(root, P + 'blipFill')
        ET.SubElement(fill, A + 'blip', {R + 'embed': 'image'})
        ET.SubElement(fill, A + 'srcRect', l='10000', r='20000')
        ET.SubElement(ET.SubElement(fill, A + 'stretch'), A + 'fillRect')
    props = ET.SubElement(root, P + ('grpSpPr' if kind == 'group' else 'spPr'))
    transform = ET.SubElement(props, A + 'xfrm')
    ET.SubElement(transform, A + 'off', x='1000000', y='1000000')
    ET.SubElement(transform, A + 'ext', cx='2000000', cy='1000000')
    if kind == 'group':
        ET.SubElement(transform, A + 'chOff', x='0', y='0')
        ET.SubElement(transform, A + 'chExt', cx='2000000', cy='1000000')
        root.append(shape(int(sid) + 100, 'text'))
        root.append(shape(int(sid) + 200, 'picture'))
    else:
        ET.SubElement(ET.SubElement(props, A + 'prstGeom', prst='rect'), A + 'avLst')
        if kind != 'picture':
            ET.SubElement(ET.SubElement(props, A + 'solidFill'), A + 'srgbClr', val='239565')
    if kind == 'text':
        body = ET.SubElement(root, P + 'txBody')
        ET.SubElement(body, A + 'bodyPr', anchor='ctr')
        ET.SubElement(body, A + 'lstStyle')
        for text in ('题干 / question', 'Answer: 42', 'x² + y² = z²'):
            paragraph = ET.SubElement(body, A + 'p')
            run = ET.SubElement(paragraph, A + 'r')
            ET.SubElement(run, A + 'rPr', sz='2000')
            ET.SubElement(run, A + 't').text = text
    return root


def effect(sid, cls='entr', trigger='clickEffect', delay=0, duration=500, preset=1, **options):
    return dict(sid=str(sid), cls=cls, trigger=trigger, delay=delay, duration=duration, preset=str(preset), **options)


def slide(objects, effects=()):
    with zipfile.ZipFile(DEMO) as archive:
        root = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
    timing = root.find(P + 'timing')
    if timing is not None:
        root.remove(timing)
    tree = root.find(P + 'cSld/' + P + 'spTree')
    for item in list(tree):
        if item.tag not in (P + 'nvGrpSpPr', P + 'grpSpPr'):
            tree.remove(item)
    for sid, kind in objects:
        tree.append(shape(sid, kind))
    if not effects:
        return root
    timing = ET.SubElement(root, P + 'timing')
    outer = ET.SubElement(ET.SubElement(timing, P + 'tnLst'), P + 'par')
    time_root = ET.SubElement(outer, P + 'cTn', id='1', dur='indefinite', nodeType='tmRoot', restart='never')
    sequence = ET.SubElement(ET.SubElement(time_root, P + 'childTnLst'), P + 'seq', concurrent='1', nextAc='seek')
    main = ET.SubElement(sequence, P + 'cTn', id='2', dur='indefinite', nodeType='mainSeq')
    children = ET.SubElement(main, P + 'childTnLst')
    next_id = 3

    def time(parent, **attrs):
        nonlocal next_id
        node = ET.SubElement(parent, P + 'cTn', id=str(next_id), **{key: str(value) for key, value in attrs.items()})
        next_id += 1
        return node

    active = None
    for event in effects:
        if active is None or event['trigger'] == 'clickEffect':
            group = time(ET.SubElement(children, P + 'par'), fill='hold')
            ET.SubElement(ET.SubElement(group, P + 'stCondLst'), P + 'cond', delay='indefinite' if event['trigger'] == 'clickEffect' else '0')
            active = ET.SubElement(group, P + 'childTnLst')
            elapsed = 0
        start = elapsed + event['delay'] if event['trigger'] == 'afterEffect' else event['delay']
        wrapper = time(ET.SubElement(active, P + 'par'), fill='hold')
        ET.SubElement(ET.SubElement(wrapper, P + 'stCondLst'), P + 'cond', delay=str(start))
        node = time(ET.SubElement(ET.SubElement(wrapper, P + 'childTnLst'), P + 'par'), presetClass=event['cls'], presetID=event['preset'], nodeType=event['trigger'], fill='hold')
        for key, value in event.get('timing', {}).items():
            node.set(key, str(value))
        behaviors = ET.SubElement(node, P + 'childTnLst')
        if event['cls'] in ('entr', 'exit'):
            behavior = ET.SubElement(behaviors, P + 'animEffect', transition='in' if event['cls'] == 'entr' else 'out', filter=event.get('filter', 'fade'))
        else:
            behavior = ET.SubElement(behaviors, P + event.get('behavior', 'animRot'), event.get('attributes', {'by': '5400000'}))
        common = ET.SubElement(behavior, P + 'cBhvr')
        time(common, dur=event['duration'], fill='hold')
        target = ET.SubElement(ET.SubElement(common, P + 'tgtEl'), P + 'spTgt', spid=event['sid'])
        if 'paragraphs' in event:
            ET.SubElement(ET.SubElement(target, P + 'txEl'), P + 'pRg', st=str(event['paragraphs'][0]), end=str(event['paragraphs'][1]))
        if 'scale' in event:
            ET.SubElement(behavior, P + 'by', x=str(event['scale'][0]), y=str(event['scale'][1]))
        elapsed = max(elapsed, start + event['duration'])
    for kind, event in (('prevCondLst', 'onPrev'), ('nextCondLst', 'onNext')):
        condition = ET.SubElement(ET.SubElement(sequence, P + kind), P + 'cond', evt=event, delay='0')
        ET.SubElement(ET.SubElement(condition, P + 'tgtEl'), P + 'sldTgt')
    return root


def write_deck(path, slides, names=None, links=(), custom_shows=()):
    names = names or ['ppt/slides/slide%d.xml' % (index + 1) for index in range(len(slides))]
    with zipfile.ZipFile(DEMO) as archive:
        parts = {name: archive.read(name) for name in archive.namelist() if not name.startswith('ppt/slides/')}
    presentation = ET.fromstring(parts['ppt/presentation.xml'])
    ids = presentation.find(P + 'sldIdLst')
    ids.clear()
    relations = ET.fromstring(parts['ppt/_rels/presentation.xml.rels'])
    for relation in list(relations):
        if relation.get('Type', '').endswith('/slide'):
            relations.remove(relation)
    types = ET.fromstring(parts['[Content_Types].xml'])
    for entry in list(types):
        if entry.get('PartName', '').startswith('/ppt/slides/'):
            types.remove(entry)
    if not any(entry.get('Extension') == 'png' for entry in types):
        ET.SubElement(types, CT + 'Default', Extension='png', ContentType='image/png')
    for index, (name, original) in enumerate(zip(names, slides)):
        root = copy.deepcopy(original)
        rid = 'testSlide%d' % index
        ET.SubElement(ids, P + 'sldId', {'id': str(256 + index), R + 'id': rid})
        ET.SubElement(relations, PR + 'Relationship', Id=rid, Type=OD + 'slide', Target=posixpath.relpath(name, 'ppt'))
        ET.SubElement(types, CT + 'Override', PartName='/' + name, ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
        slide_relations = ET.Element(PR + 'Relationships')
        for relation_id, relation_type, target in [('layout', 'slideLayout', 'ppt/slideLayouts/slideLayout1.xml'), ('image', 'image', 'ppt/media/test.png')]:
            ET.SubElement(slide_relations, PR + 'Relationship', Id=relation_id, Type=OD + relation_type, Target=posixpath.relpath(target, posixpath.dirname(name)))
        for source_index, target_index in links:
            if index != source_index:
                continue
            nv = root.find('.//' + P + 'sp/' + P + 'nvSpPr/' + P + 'cNvPr')
            ET.SubElement(nv, A + 'hlinkClick', {R + 'id': 'jump', 'action': 'ppaction://hlinksldjump'})
            ET.SubElement(slide_relations, PR + 'Relationship', Id='jump', Type=OD + 'slide', Target=posixpath.relpath(names[target_index], posixpath.dirname(name)))
        parts[name] = ET.tostring(root)
        rel_name = posixpath.join(posixpath.dirname(name), '_rels', posixpath.basename(name) + '.rels')
        parts[rel_name] = ET.tostring(slide_relations)
    if custom_shows:
        shows = ET.Element(P + 'custShowLst')
        for index, sequence in enumerate(custom_shows):
            show = ET.SubElement(shows, P + 'custShow', name='Show%d' % index, id=str(index))
            listing = ET.SubElement(show, P + 'sldLst')
            for page in sequence:
                ET.SubElement(listing, P + 'sld', {R + 'id': 'testSlide%d' % page})
        style = presentation.find(P + 'defaultTextStyle')
        presentation.insert(list(presentation).index(style) if style is not None else len(presentation), shows)
    parts['ppt/presentation.xml'] = ET.tostring(presentation)
    parts['ppt/_rels/presentation.xml.rels'] = ET.tostring(relations)
    parts['[Content_Types].xml'] = ET.tostring(types)
    parts['ppt/media/test.png'] = PIXEL
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def rewrite(source, output, part, change):
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as after:
        for entry in before.infolist():
            data = before.read(entry.filename)
            if entry.filename == part:
                root = ET.fromstring(data)
                change(root)
                data = ET.tostring(root)
            after.writestr(entry, data)


def add_interactive(root, trigger, events, restart='whenNotActive'):
    model = slide([], events)
    model_timing = model.find(P + 'timing')
    sequence = copy.deepcopy(model_timing.find('.//' + P + 'seq'))
    timing = root.find(P + 'timing')
    if timing is None:
        timing = copy.deepcopy(model_timing)
        time_root = next(n for n in timing.iter(P + 'cTn') if n.get('nodeType') == 'tmRoot')
        time_root.find(P + 'childTnLst').clear()
        root.append(timing)
    else:
        time_root = next(n for n in timing.iter(P + 'cTn') if n.get('nodeType') == 'tmRoot')
    last_id = max(int(n.get('id')) for n in timing.iter(P + 'cTn'))
    mapping = {n.get('id'): str(last_id + index + 1) for index, n in enumerate(sequence.iter(P + 'cTn'))}
    for node in sequence.iter(P + 'cTn'):
        node.set('id', mapping[node.get('id')])
    for reference in sequence.iter(P + 'tn'):
        reference.set('val', mapping.get(reference.get('val'), reference.get('val')))
    channel = sequence.find(P + 'cTn')
    channel.set('nodeType', 'interactiveSeq')
    channel.set('restart', restart)
    channel.set('evtFilter', 'cancelBubble')
    channel.attrib.pop('dur', None)
    start_conditions = ET.Element(P + 'stCondLst')
    channel.insert(0, start_conditions)
    condition = ET.SubElement(start_conditions, P + 'cond', evt='onClick', delay='0')
    ET.SubElement(ET.SubElement(condition, P + 'tgtEl'), P + 'spTgt', spid=str(trigger))
    synchronization = ET.Element(P + 'endSync', evt='end', delay='0')
    ET.SubElement(synchronization, P + 'rtn', val='all')
    channel.insert(1, synchronization)
    first = channel.find(P + 'childTnLst/' + P + 'par/' + P + 'cTn/' + P + 'stCondLst/' + P + 'cond')
    if first is not None:
        first.set('delay', '0')
    for name in ('prevCondLst', 'nextCondLst'):
        for listing in list(sequence.findall(P + name)):
            sequence.remove(listing)
    condition = ET.SubElement(ET.SubElement(sequence, P + 'nextCondLst'), P + 'cond', evt='onClick', delay='0')
    ET.SubElement(ET.SubElement(condition, P + 'tgtEl'), P + 'spTgt', spid=str(trigger))
    time_root.find(P + 'childTnLst').append(sequence)
    return channel
