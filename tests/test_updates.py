from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from pptx_animation_split.cli import main
from pptx_animation_split.updates import API_URL, REPOSITORY, check_update, fetch_json, plugin_version, version_key


DEMO = Path(__file__).resolve().parents[1] / 'examples/demo.pptx'


def release(version, *, prerelease=False):
    names = ['pptx-animation-split-%s-%s.zip' % (version, kind) for kind in ('tool', 'skill')]
    return {
        'tag_name': 'v' + version, 'prerelease': prerelease, 'draft': False,
        'published_at': '2026-11-12T00:00:00Z', 'body': 'Changes for ' + version,
        'assets': [{'name': name} for name in [*names, 'release.json']],
    }


def manifest(version):
    return {
        'schema_version': 1, 'cli_api': 1, 'version': version, 'requires_python': [3, 10], 'publishable': True,
        'assets': {kind: {'name': 'pptx-animation-split-%s-%s.zip' % (version, kind), 'sha256': 'a' * 64} for kind in ('tool', 'skill')},
    }


class UpdateTests(unittest.TestCase):
    def query(self, versions, documents=None, **kwargs):
        documents = documents or {}
        def fetch(url, timeout):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 3)
            if url == API_URL:
                return versions
            version = url.split('/')[-2].removeprefix('v')
            self.assertEqual(url, REPOSITORY + '/releases/download/v' + version + '/release.json')
            return documents.get(version, manifest(version))
        with patch('pptx_animation_split.updates.fetch_json', side_effect=fetch):
            return check_update(**kwargs)

    def test_numeric_prerelease_order_and_generated_plugin_version(self):
        self.assertLess(version_key('0.1.0a9'), version_key('v0.1.0a10'))
        self.assertLess(version_key('0.1.0a10'), version_key('0.1.0b1'))
        self.assertLess(version_key('0.1.0rc9'), version_key('0.1.0'))
        self.assertEqual(plugin_version('0.1.0a4'), '0.1.0-alpha.4')
        self.assertEqual(plugin_version('1.2.3'), '1.2.3')

    def test_preview_installation_finds_new_preview_and_supplies_matching_downloads(self):
        result = self.query([release('0.1.0a10', prerelease=True), release('0.1.0a9', prerelease=True)], current='0.1.0a4')
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(result['latest_version'], '0.1.0a10')
        self.assertTrue(result['downloads']['skill'].endswith('/v0.1.0a10/pptx-animation-split-0.1.0a10-skill.zip'))
        self.assertIn('Changes', result['notes'])

    def test_stable_installation_skips_previews_unless_requested(self):
        versions = [release('1.1.0a1', prerelease=True), release('1.0.1')]
        self.assertEqual(self.query(versions, current='1.0.0')['latest_version'], '1.0.1')
        self.assertEqual(self.query(versions, current='1.0.0', include_prereleases=True)['latest_version'], '1.1.0a1')

    def test_drafts_unpublished_and_unrecognized_tags_are_not_updates(self):
        versions = [release('2.0.0'), release('3.0.0'), release('4.0.0')]
        versions[0]['draft'] = True
        versions[1]['published_at'] = None
        versions[2]['tag_name'] = 'nightly'
        self.assertEqual(self.query(versions, current='1.0.0')['status'], 'up_to_date')

    def test_update_requires_both_bundles_and_release_manifest(self):
        for missing in ('tool.zip', 'skill.zip', 'release.json'):
            with self.subTest(missing=missing):
                item = release('1.0.1')
                item['assets'] = [asset for asset in item['assets'] if not asset['name'].endswith(missing)]
                result = self.query([item], current='1.0.0')
                self.assertEqual(result['status'], 'no_compatible_update')
                self.assertNotIn('downloads', result)

    def test_incompatible_latest_falls_back_to_newest_compatible_release(self):
        newer = manifest('1.2.0')
        newer['requires_python'] = [3, 15]
        result = self.query([release('1.1.0'), release('1.2.0')], {'1.2.0': newer}, current='1.0.0', python_version=(3, 12))
        self.assertEqual(result['latest_version'], '1.1.0')
        self.assertIn('skipped', result)

    def test_local_mixed_or_future_metadata_is_not_offered(self):
        mutations = [
            {'schema_version': 2}, {'cli_api': 2}, {'version': '1.0.2'}, {'publishable': False},
            {'requires_python': '>=3.10'}, {'assets': {}},
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                document = manifest('1.0.1')
                document.update(mutation)
                self.assertEqual(self.query([release('1.0.1')], {'1.0.1': document}, current='1.0.0')['status'], 'no_compatible_update')

    def test_remote_download_url_cannot_redirect_update_instructions(self):
        item = release('1.0.1')
        for asset in item['assets']:
            asset['browser_download_url'] = 'https://unrelated.invalid/command'
        result = self.query([item], current='1.0.0')
        self.assertTrue(all(url.startswith(REPOSITORY + '/releases/download/') for url in result['downloads'].values()))

    def test_network_failures_and_invalid_data_are_reported_without_raising(self):
        for error in (URLError('offline'), TimeoutError('timeout'), HTTPError(API_URL, 403, 'rate limited', {}, None), ValueError('invalid JSON')):
            with self.subTest(error=error), patch('pptx_animation_split.updates.fetch_json', side_effect=error):
                self.assertEqual(check_update()['status'], 'unavailable')
        with patch('pptx_animation_split.updates.fetch_json', return_value={'unexpected': True}):
            self.assertEqual(check_update()['status'], 'unavailable')
        item = release('1.0.1')
        item['assets'] = None
        with patch('pptx_animation_split.updates.fetch_json', return_value=[item]):
            self.assertEqual(check_update(current='1.0.0')['status'], 'unavailable')

    def test_mismatched_published_asset_digest_is_not_offered(self):
        item = release('1.0.1')
        item['assets'][0]['digest'] = 'sha256:' + 'b' * 64
        self.assertEqual(self.query([item], current='1.0.0')['status'], 'no_compatible_update')

    def test_json_fetch_sends_no_credentials_and_limits_response_size(self):
        with patch('pptx_animation_split.updates.urlopen') as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b'[]'
            self.assertEqual(fetch_json(API_URL, 2), [])
            request = open_url.call_args.args[0]
            self.assertFalse(request.has_header('Authorization'))
            self.assertIsNone(request.data)
            self.assertEqual(open_url.return_value.__enter__.return_value.read.call_args.args[0], 1024 * 1024 + 1)
            open_url.return_value.__enter__.return_value.read.return_value = b'x' * (1024 * 1024 + 1)
            with self.assertRaises(ValueError):
                fetch_json(API_URL, 2)

    def test_offline_skill_split_still_succeeds_and_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'static.pptx'
            before = DEMO.read_bytes()
            result = {'status': 'unavailable', 'current_version': '0.1.0a4', 'releases_url': REPOSITORY + '/releases'}
            errors = io.StringIO()
            with patch('pptx_animation_split.updates.check_update', return_value=result), redirect_stdout(io.StringIO()), redirect_stderr(errors):
                self.assertEqual(main(['split', str(DEMO), str(output)], notify_updates=True), 0)
            self.assertTrue(output.is_file())
            self.assertEqual(DEMO.read_bytes(), before)
            self.assertIn('继续使用', errors.getvalue())

    def test_standalone_or_opted_out_splitting_never_queries_network(self):
        for notify, arguments in ((False, []), (True, ['--no-update-check'])):
            with self.subTest(notify=notify), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / 'static.pptx'
                with patch('pptx_animation_split.updates.check_update') as check, redirect_stdout(io.StringIO()):
                    self.assertEqual(main([*arguments, 'split', str(DEMO), str(output)], notify_updates=notify), 0)
                    check.assert_not_called()
        with tempfile.TemporaryDirectory() as temporary, patch.dict('os.environ', {'PPTX_ANIMATION_SPLIT_NO_UPDATE_CHECK': '1'}):
            with patch('pptx_animation_split.updates.check_update') as check, redirect_stdout(io.StringIO()):
                self.assertEqual(main(['split', str(DEMO), str(Path(temporary) / 'static.pptx')], notify_updates=True), 0)
                check.assert_not_called()

    def test_cli_update_json_and_invalid_timeout(self):
        output = io.StringIO()
        with patch('pptx_animation_split.updates.fetch_json', return_value=[]), redirect_stdout(output):
            self.assertEqual(main(['check-update', '--json']), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'up_to_date')
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(['check-update', '--timeout', '0']), 1)


if __name__ == '__main__':
    unittest.main()
