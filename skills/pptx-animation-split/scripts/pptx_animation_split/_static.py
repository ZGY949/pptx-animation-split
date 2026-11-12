import copy
import xml.etree.ElementTree as ET


P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def transient_prefixes(effects):
    entered = {}
    prefixes = set()
    for index, event in enumerate(effects):
        key = (event.get('spid'), event.get('prg'))
        if event['cls'] == 'entr':
            entered[key] = event
        elif event['cls'] == 'exit':
            entrance = entered.pop(key, None)
            if (entrance is None or not key[0] or entrance.get('looping') or event.get('looping')
                    or event.get('end', 0) <= entrance.get('start', 0)):
                continue
            boundary = next(i for i, previous in enumerate(effects[:index + 1])
                            if previous['cls'] == 'exit' and previous.get('end') == event.get('end'))
            prefixes.add(boundary)
    return sorted(prefixes)


def groups_for_state(groups, step, prefix=None):
    if prefix is None:
        return groups
    view = copy.copy(groups)
    if not hasattr(view, 'initial'):
        from ._core import AnimationGroups
        view = AnimationGroups()
        view.extend(groups)
    view.initial = list(getattr(groups, 'initial', []))
    view.declared = getattr(groups, 'declared', [
        event for effects in [getattr(groups, 'initial', [])] + list(groups) for event in effects
    ])
    if step == -1:
        view.initial = view.initial[:prefix]
    else:
        view[step] = list(groups[step][:prefix])
    return view


def static_state_plan(xml_bytes, groups, slide_size, render):
    states = []
    notices = []
    previous = None
    for step, effects in enumerate([getattr(groups, 'initial', [])] + list(groups), -1):
        for prefix in transient_prefixes(effects) + [None]:
            view = groups_for_state(groups, step, prefix)
            root = render(xml_bytes, view, step, slide_size)
            scene = root.find(P + 'cSld')
            current = ET.tostring(scene if scene is not None else root)
            media_only = bool(effects) and all(
                event['cls'] == 'mediacall' and not event.get('changes') for event in effects
            )
            if current == previous and (prefix is not None or media_only):
                if prefix is None:
                    notices.append('点击步骤%d仅含媒体控制且画面未变，合并重复页' % (step + 1))
                continue
            states.append((step, prefix))
            previous = current
            if prefix is not None:
                notices.append('步骤%d保留短暂显隐对象的完整可见状态；不是动画过程的逐帧截图' % (step + 1))
    return states, notices
