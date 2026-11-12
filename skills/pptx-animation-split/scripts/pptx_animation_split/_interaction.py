import copy
import itertools
import xml.etree.ElementTree as ET


P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def expand_interactions(root, click_order, parse_linear, group_type, visibility):
    timing = root.find(P + 'timing')
    if timing is None:
        if click_order:
            raise ValueError('本页没有可执行的动画点击步骤')
        return parse_linear(root)
    nodes = [node for node in timing.iter(P + 'cTn') if node.get('nodeType') in ('mainSeq', 'interactiveSeq')]
    interactive = [node for node in nodes if node.get('nodeType') == 'interactiveSeq']
    if not interactive and click_order is None:
        return parse_linear(root)
    root = copy.deepcopy(root)
    timing = root.find(P + 'timing')
    used_ids = {node.get('id') for node in timing.iter(P + 'cTn') if node.get('id')}
    for index, node in enumerate(timing.iter(P + 'cTn')):
        if node.get('id') is None:
            identity = 'split-time-%d' % index
            while identity in used_ids:
                identity += '-x'
            node.set('id', identity)
            used_ids.add(identity)
    nodes = [node for node in timing.iter(P + 'cTn') if node.get('nodeType') in ('mainSeq', 'interactiveSeq')]
    interactive = [node for node in nodes if node.get('nodeType') == 'interactiveSeq']
    notes = []
    parents = {child: parent for parent in timing.iter() for child in parent}
    identifiers = [node.get('id') for node in timing.iter(P + 'cTn') if node.get('id')]
    if len(identifiers) != len(set(identifiers)):
        notes.append('动画时间节点 ID 重复，事件依赖不明确')
    order = {node.get('id'): index for index, node in enumerate(timing.iter(P + 'cTn')) if node.get('presetID')}
    mains = [node for node in nodes if node.get('nodeType') == 'mainSeq']
    if len(mains) > 1:
        notes.append('存在多个主动画序列，尚未支持')
    shape_ids = {node.get('id') for node in root.iter(P + 'cNvPr')}
    shape_names = {node.get('id'): node.get('name', '') for node in root.iter(P + 'cNvPr')}
    shape_ancestors = {}
    root_parents = {child: parent for parent in root.iter() for child in parent}
    for nonvisual in root.iter(P + 'cNvPr'):
        chain = []
        owner = root_parents.get(root_parents.get(nonvisual))
        ancestor = root_parents.get(owner)
        while ancestor is not None:
            if ancestor.tag == P + 'grpSp':
                identity = ancestor.find(P + 'nvGrpSpPr/' + P + 'cNvPr')
                if identity is not None:
                    chain.append(identity.get('id'))
            ancestor = root_parents.get(ancestor)
        shape_ancestors[nonvisual.get('id')] = chain
    channels = []
    covered = set()
    for node in nodes:
        if parents.get(node) is None or parents[node].tag != P + 'seq':
            notes.append('交互展开要求标准的顺序时间容器')
            continue
        ancestor = parents.get(node)
        while ancestor is not None:
            if ancestor in nodes:
                notes.append('交互与主序列嵌套尚未支持')
                break
            ancestor = parents.get(ancestor)
        trigger = None
        delay = 0
        if node in interactive:
            conditions = [condition for condition in node.findall(P + 'stCondLst/' + P + 'cond')
                          if not (condition.get('evt') is None and condition.get('delay') == 'indefinite')]
            targets = {condition.find(P + 'tgtEl/' + P + 'spTgt').get('spid')
                       for condition in conditions if condition.get('evt') == 'onClick'
                       and condition.find(P + 'tgtEl/' + P + 'spTgt') is not None}
            if len(conditions) != 1 or len(targets) != 1:
                notes.append('交互序列没有唯一的对象点击触发器')
                continue
            trigger = next(iter(targets))
            if not trigger or trigger not in shape_ids:
                notes.append('交互触发对象不存在：%s' % trigger)
                continue
            if not conditions[0].get('delay', '0').isdecimal():
                notes.append('交互触发延时无法求值')
                continue
            delay = int(conditions[0].get('delay', '0'))
            for condition in parents[node].findall(P + 'nextCondLst/' + P + 'cond'):
                target = condition.find(P + 'tgtEl/' + P + 'spTgt')
                if condition.get('evt') != 'onClick' or target is None or target.get('spid') != trigger:
                    notes.append('交互序列的后续点击对象与触发器不一致')
        channel_root = copy.deepcopy(root)
        channel_root.remove(channel_root.find(P + 'timing'))
        channel_timing = ET.SubElement(channel_root, P + 'timing')
        outer = ET.SubElement(ET.SubElement(channel_timing, P + 'tnLst'), P + 'par')
        original_root = next((n for n in timing.iter(P + 'cTn') if n.get('nodeType') == 'tmRoot'), None)
        time_root = ET.SubElement(outer, P + 'cTn', id=original_root.get('id', 'split-root') if original_root is not None else 'split-root', nodeType='tmRoot', dur='indefinite')
        sequence = copy.deepcopy(parents[node])
        selected = sequence.find(P + 'cTn')
        selected.set('nodeType', 'mainSeq')
        if trigger is not None:
            if selected.get('evtFilter') == 'cancelBubble':
                selected.attrib.pop('evtFilter')
            if selected.get('restart', 'always') not in ('always', 'whenNotActive', 'never'):
                notes.append('交互序列的重新触发规则无法识别')
            conditions = selected.find(P + 'stCondLst')
            if conditions is not None:
                selected.remove(conditions)
        ET.SubElement(time_root, P + 'childTnLst').append(sequence)
        groups, warnings = parse_linear(channel_root)
        notes.extend(warnings)
        events = list(itertools.chain(getattr(groups, 'initial', []), *groups))
        for event in events:
            event['order'] = order.get(event.get('time_id'), event['order'])
            if trigger is not None and event['cls'] in ('emph', 'path'):
                event['replay_key'] = (node.get('id'), event.get('time_id'))
        covered.update(n.get('id') for n in node.iter(P + 'cTn') if n.get('presetID'))
        steps = list(groups)
        initial = getattr(groups, 'initial', [])
        if trigger is not None and initial:
            if steps:
                steps[0] = initial + steps[0]
            else:
                steps = [initial]
        channels.append(dict(trigger=trigger, steps=steps, initial=initial if trigger is None else [], events=events,
                             restart=node.get('restart', 'always'), delay=delay, info=getattr(groups, 'info', [])))
    inside_channels = {id(descendant) for channel in nodes for descendant in channel.iter(P + 'cTn')}
    for node in timing.iter(P + 'cTn'):
        if node.get('presetID') and node.get('id') not in covered:
            notes.append('交互展开存在未处理的动画效果：%s' % node.get('presetID'))
        if id(node) not in inside_channels and (
            node.get('repeatCount') not in (None, '1000') or node.get('repeatDur') is not None
        ):
            notes.append('主序列和交互序列外部容器的重复尚未支持')
        if id(node) not in inside_channels and (
            node.get('spd') not in (None, '100000') or node.get('autoRev') in ('1', 'true')
            or node.get('tmFilter') or node.get('evtFilter') or node.find(P + 'endCondLst') is not None
            or any(condition.get('evt') is not None or condition.get('delay') == 'indefinite'
                   for condition in node.findall(P + 'stCondLst/' + P + 'cond'))
        ):
            notes.append('主序列和交互序列外部容器的时间修饰尚未支持')
    for behavior in timing.iter():
        if behavior.tag not in {P + tag for tag in ('anim', 'animClr', 'animEffect', 'animMotion', 'animRot', 'animScale', 'set', 'cmd', 'audio', 'video')}:
            continue
        ancestor = parents.get(behavior)
        while ancestor is not None and ancestor not in nodes:
            ancestor = parents.get(ancestor)
        if ancestor is None:
            notes.append('主序列及对象触发序列之外的动画行为尚未支持')
    result = group_type()
    result.initial = list(itertools.chain.from_iterable(channel['initial'] for channel in channels))
    result.declared = list(itertools.chain.from_iterable(channel['events'] for channel in channels))
    result.info = list(itertools.chain.from_iterable(channel['info'] for channel in channels))
    main = [channel for channel in channels if channel['trigger'] is None]
    by_trigger = {}
    for channel in channels:
        if channel['trigger'] is not None:
            by_trigger.setdefault(channel['trigger'], []).append(channel)
    if click_order is None:
        route = ['next'] * sum(len(channel['steps']) for channel in main)
        for target, linked in by_trigger.items():
            route.extend(['shape:' + target] * max(len(channel['steps']) for channel in linked))
    else:
        route = list(click_order)
    if any(not isinstance(action, str) for action in route):
        raise ValueError('点击顺序只接受 next 或 shape:对象编号')
    cursors = {id(channel): 0 for channel in channels}
    main_steps = list(itertools.chain.from_iterable(channel['steps'] for channel in main))
    main_cursor = 0
    result.actions = []
    for action in route:
        if action == 'next':
            if main_cursor >= len(main_steps):
                raise ValueError('点击顺序中的 next 超出了本页普通动画步骤')
            effects = copy.deepcopy(main_steps[main_cursor])
            main_cursor += 1
        elif action.startswith('shape:'):
            target = action[6:]
            if target not in by_trigger:
                raise ValueError('点击顺序引用了未知触发对象：%s' % target)
            hidden, _ = visibility(result, len(result) - 1)
            if any(sid in hidden for sid in [target] + shape_ancestors.get(target, [])):
                raise ValueError('按当前点击顺序，触发对象 %s 不可见；请用 --click-order 调整顺序' % target)
            effects = []
            for channel in by_trigger[target]:
                cursor = cursors[id(channel)]
                if cursor >= len(channel['steps']):
                    if channel['restart'] == 'never':
                        continue
                    cursor = 0
                if channel['steps']:
                    events = copy.deepcopy(channel['steps'][cursor])
                    for event in events:
                        event['start'] += channel['delay'] if cursor == 0 else 0
                        event['end'] += channel['delay'] if cursor == 0 else 0
                    effects.extend(events)
                cursors[id(channel)] = cursor + 1
        else:
            raise ValueError('无法识别点击步骤：%s；应为 next 或 shape:对象编号' % action)
        effects.sort(key=lambda event: event['start'] if event['cls'] == 'entr' else event['end'])
        for index, left in enumerate(effects):
            for right in effects[index + 1:]:
                properties = {change['kind'] for change in left.get('changes') or []} & {change['kind'] for change in right.get('changes') or []}
                loop_visibility = (left.get('looping') or right.get('looping')) and left['cls'] in ('entr', 'exit') and right['cls'] in ('entr', 'exit')
                left_end = float('inf') if left.get('looping') else left['end']
                right_end = float('inf') if right.get('looping') else right['end']
                if left['spid'] == right['spid'] and (properties or loop_visibility) and max(left['start'], right['start']) < min(left_end, right_end):
                    notes.append('同一触发动作内，同一对象属性存在重叠动画')
        result.append(effects)
        result.actions.append(action)
    if interactive:
        result.info.append('对象触发展开顺序：' + ' → '.join(route))
        result.info.extend('触发对象 shape:%s：%s' % (target, shape_names.get(target, '')) for target in by_trigger)
    return result, list(dict.fromkeys(notes))
