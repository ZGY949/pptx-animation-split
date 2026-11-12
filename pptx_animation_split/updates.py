import json
from http.client import HTTPException
import re
import sys
import time
from urllib.request import Request, urlopen

from . import __version__


REPOSITORY = 'https://github.com/ZGY949/pptx-animation-split'
RELEASES_URL = REPOSITORY + '/releases'
API_URL = 'https://api.github.com/repos/ZGY949/pptx-animation-split/releases?per_page=100'
CLI_API = 1
MAX_RESPONSE = 1024 * 1024
VERSION = re.compile(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:(a|b|rc)(0|[1-9]\d*))?\Z')


def version_key(value):
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError('无法识别版本号：%s' % value)
    major, minor, patch, stage, number = match.groups()
    return (int(major), int(minor), int(patch), {None: 3, 'rc': 2, 'b': 1, 'a': 0}[stage], int(number or 0))


def plugin_version(value):
    version_key(value)
    return re.sub(r'(a|b|rc)(\d+)$', lambda match: '-' + {'a': 'alpha', 'b': 'beta', 'rc': 'rc'}[match[1]] + '.' + match[2], value)


def fetch_json(url, timeout):
    request = Request(url, headers={
        'Accept': 'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/json',
        'User-Agent': 'pptx-animation-split/' + __version__,
    })
    with urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE + 1)
    if len(data) > MAX_RESPONSE:
        raise ValueError('版本信息过大')
    return json.loads(data)


def check_update(*, current=__version__, include_prereleases=None, timeout=3.0, python_version=None):
    current_key = version_key(current)
    if not 0 < timeout <= 15:
        raise ValueError('更新检查超时须大于 0 且不超过 15 秒')
    if include_prereleases is None:
        include_prereleases = current_key[3] < 3
    python_version = tuple(python_version or sys.version_info[:2])
    result = {'status': 'up_to_date', 'current_version': current, 'releases_url': RELEASES_URL}
    deadline = time.monotonic() + timeout

    def read(url):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('更新检查超时')
        return fetch_json(url, remaining)

    try:
        releases = read(API_URL)
        if not isinstance(releases, list):
            raise ValueError('版本列表格式错误')
        candidates = []
        for release in releases:
            if not isinstance(release, dict) or release.get('draft') or not release.get('published_at'):
                continue
            try:
                key = version_key(release.get('tag_name'))
            except ValueError:
                continue
            if (release.get('prerelease') or key[3] < 3) and not include_prereleases:
                continue
            if key > current_key:
                candidates.append((key, release))
        skipped = []
        for key, release in sorted(candidates, key=lambda item: item[0], reverse=True):
            tag = release['tag_name']
            version = tag.removeprefix('v')
            assets = {asset.get('name'): asset for asset in release.get('assets', []) if isinstance(asset, dict)}
            names = {kind: 'pptx-animation-split-%s-%s.zip' % (version, kind) for kind in ('tool', 'skill')}
            if not all(name in assets for name in [*names.values(), 'release.json']):
                skipped.append(tag + ': 缺少配套安装包或版本清单')
                continue
            base = REPOSITORY + '/releases/download/' + tag + '/'
            metadata = read(base + 'release.json')
            if not isinstance(metadata, dict):
                raise ValueError('发布清单格式错误')
            minimum = metadata.get('requires_python')
            compatible = (
                metadata.get('schema_version') == 1 and metadata.get('cli_api') == CLI_API
                and metadata.get('version') == version and metadata.get('publishable') is True
                and isinstance(minimum, list) and len(minimum) == 2
                and all(type(part) is int and part >= 0 for part in minimum)
                and python_version >= tuple(minimum)
            )
            declared_assets = metadata.get('assets', {})
            if not isinstance(declared_assets, dict):
                compatible = False
            else:
                for kind, name in names.items():
                    asset = declared_assets.get(kind, {})
                    if not isinstance(asset, dict) or asset.get('name') != name or not re.fullmatch(r'[0-9a-f]{64}', str(asset.get('sha256', ''))):
                        compatible = False
                    elif assets[name].get('digest') and assets[name]['digest'] != 'sha256:' + asset['sha256']:
                        compatible = False
            if not compatible:
                skipped.append(tag + ': 版本清单、Python 或调用接口不兼容')
                continue
            result.update({
                'status': 'update_available', 'latest_version': version,
                'release_url': REPOSITORY + '/releases/tag/' + tag,
                'downloads': {kind: base + name for kind, name in names.items()},
                'sha256': {kind: declared_assets[kind]['sha256'] for kind in names},
                'notes': str(release.get('body') or '')[:2000],
            })
            if skipped:
                result['skipped'] = skipped
            return result
        if skipped:
            result.update(status='no_compatible_update', skipped=skipped)
        return result
    except (OSError, HTTPException, ValueError, TypeError, AttributeError) as error:
        result.update(status='unavailable', reason=str(error))
        return result


def update_message(result):
    if result['status'] == 'update_available':
        return '发现兼容新版 %s（当前 %s）：%s；请按安装说明更新，程序未自动替换。' % (
            result['latest_version'], result['current_version'], result['release_url'])
    if result['status'] == 'unavailable':
        return '暂时无法检查更新；继续使用本地 %s。可手动查看：%s' % (result['current_version'], result['releases_url'])
    if result['status'] == 'no_compatible_update':
        return '存在更新的发布记录，但尚未确认兼容安装包；继续使用本地 %s。%s' % (result['current_version'], result['releases_url'])
    return '当前 %s；本次查询未发现更高的兼容发布版本。' % result['current_version']
