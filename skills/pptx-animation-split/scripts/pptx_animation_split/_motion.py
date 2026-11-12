import math
import re


NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
TOKEN = re.compile(r'[MLCZEmlcze]|' + NUMBER)


def motion_endpoint(path):
    matches = list(TOKEN.finditer(path))
    boundary = 0
    tokens = []
    for match in matches:
        if path[boundary:match.start()].strip(' \t\r\n,'):
            return None
        tokens.append(match.group())
        boundary = match.end()
    if path[boundary:].strip(' \t\r\n,') or not tokens:
        return None
    current = (0.0, 0.0)
    start = None
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command.upper() == 'E':
            return current if start is not None else None
        if command.upper() == 'Z':
            if start is None:
                return None
            current = start
            continue
        count = {'M': 2, 'L': 2, 'C': 6}.get(command.upper())
        if count is None or index + count > len(tokens):
            return None
        try:
            values = [float(value) for value in tokens[index:index + count]]
        except ValueError:
            return None
        if not all(math.isfinite(value) for value in values):
            return None
        if any(re.match(r'[-+]?\.', value) for value in tokens[index:index + count]):
            return None
        index += count
        end = (values[-2], values[-1])
        current = end if command.isupper() else (current[0] + end[0], current[1] + end[1])
        if command.upper() == 'M':
            start = current
        elif start is None:
            return None
    return current if start is not None else None
