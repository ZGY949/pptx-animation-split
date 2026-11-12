from fractions import Fraction


def repetition(node, simple_duration):
    count_value = node.get('repeatCount')
    duration_value = node.get('repeatDur')
    reverse = node.get('autoRev') in ('1', 'true')
    period = Fraction(simple_duration) * (2 if reverse else 1)
    if count_value is None and duration_value is None:
        return period, 1, False
    if period <= 0:
        raise ValueError('重复动画缺少可求值的正持续时间')
    if count_value not in (None, 'indefinite') and not count_value.isdecimal():
        raise ValueError('无法解释重复次数：%s' % count_value)
    if duration_value not in (None, 'indefinite') and not duration_value.isdecimal():
        raise ValueError('无法解释重复持续时间：%s' % duration_value)
    limits = []
    if count_value not in (None, 'indefinite'):
        limits.append(period * Fraction(int(count_value), 1000))
    if duration_value not in (None, 'indefinite'):
        limits.append(Fraction(int(duration_value)))
    if not limits:
        return period, 1, True
    duration = min(limits)
    cycles = duration / period
    if cycles.denominator != 1 or cycles <= 0:
        raise ValueError('重复动画停在非完整周期，尚不能可靠求静态终态')
    return duration, int(cycles), False
