import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pptx_animation_split import __version__
from pptx_animation_split.bundle import file_hashes
from pptx_animation_split.updates import plugin_version
from tools.build_release import build_release
from tools.package_source import source_files


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temporary.name)
        cls.artifacts = cls.work / 'artifacts'
        cls.result = build_release(cls.artifacts, local=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def install(self, kind):
        destination = self.work / self.id().split('.')[-1] / kind
        with zipfile.ZipFile(self.artifacts / self.result['assets'][kind]['name']) as archive:
            archive.extractall(destination)
        return next(destination.iterdir())

    def launch(self, launcher, *args):
        return subprocess.run([sys.executable, '-I', '-B', str(launcher), *map(str, args)], cwd=self.work, text=True, capture_output=True, timeout=30)

    def test_both_archives_run_independently_and_leave_installation_unchanged(self):
        for kind in ('tool', 'skill'):
            with self.subTest(kind=kind):
                package = self.install(kind)
                launcher = package / ('run.py' if kind == 'tool' else 'skills/pptx-animation-split/scripts/run.py')
                before = file_hashes(package)
                self.assertEqual(self.launch(launcher, '--version').stdout.strip(), __version__)
                output = self.work / ('isolated-' + kind + '.pptx')
                split = self.launch(launcher, '--no-update-check', 'split', ROOT / 'examples/demo.pptx', output)
                self.assertEqual(split.returncode, 0, split.stderr)
                self.assertEqual(self.launch(launcher, 'verify', ROOT / 'examples/demo.pptx', output).returncode, 0)
                self.assertEqual(file_hashes(package), before)
                self.assertFalse(list(package.rglob('__pycache__')))

    def test_packaged_engines_are_identical_and_metadata_matches_archives(self):
        engine = None
        metadata = json.loads((self.artifacts / 'release.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['version'], __version__)
        self.assertFalse(metadata['publishable'])
        for kind, asset in metadata['assets'].items():
            self.assertEqual(hashlib.sha256((self.artifacts / asset['name']).read_bytes()).hexdigest(), asset['sha256'])
            package = self.install(kind)
            root = package / ('pptx_animation_split' if kind == 'tool' else 'skills/pptx-animation-split/scripts/pptx_animation_split')
            hashes = file_hashes(root)
            if engine is not None:
                self.assertEqual(hashes, engine)
            engine = hashes
            if kind == 'skill':
                for manifest in ('plugin.json', '.codex-plugin/plugin.json'):
                    self.assertEqual(json.loads((package / manifest).read_text())['version'], plugin_version(__version__))

    def test_tool_package_contains_no_skill_instructions_or_development_files(self):
        package = self.install('tool')
        names = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file()}
        self.assertNotIn('SKILL.md', {Path(name).name for name in names})
        self.assertFalse(names & {'pyproject.toml', 'CONTRIBUTING.md', 'plugin.json'})
        self.assertFalse(any(name.startswith(('tests/', 'tools/', 'skills/', '.github/')) for name in names))

    def test_modified_engine_or_instruction_file_is_rejected_without_output(self):
        for relative in ('scripts/pptx_animation_split/_motion.py', 'SKILL.md'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                with zipfile.ZipFile(self.artifacts / self.result['assets']['skill']['name']) as archive:
                    archive.extractall(temporary)
                skill = next(Path(temporary).iterdir()) / 'skills/pptx-animation-split'
                path = skill / relative
                path.write_bytes(path.read_bytes() + b'\n')
                output = Path(temporary) / 'output.pptx'
                result = self.launch(skill / 'scripts/run.py', '--no-update-check', 'split', ROOT / 'examples/demo.pptx', output)
                self.assertEqual(result.returncode, 1)
                self.assertIn('已修改', result.stderr)
                self.assertFalse(output.exists())

    def test_missing_or_mixed_version_manifest_is_rejected(self):
        for mode in ('missing', 'mixed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                with zipfile.ZipFile(self.artifacts / self.result['assets']['tool']['name']) as archive:
                    archive.extractall(temporary)
                package = next(Path(temporary).iterdir())
                manifest = package / 'bundle.json'
                if mode == 'missing':
                    manifest.unlink()
                else:
                    data = json.loads(manifest.read_text())
                    data['version'] = '99.0.0'
                    manifest.write_text(json.dumps(data))
                result = self.launch(package / 'run.py', '--version')
                self.assertEqual(result.returncode, 1)

    def test_existing_destination_is_not_changed(self):
        before = file_hashes(self.artifacts)
        with self.assertRaises(ValueError):
            build_release(self.artifacts, local=True)
        self.assertEqual(file_hashes(self.artifacts), before)

    def test_official_build_requires_clean_committed_source(self):
        destination = self.work / 'rejected'
        with patch('tools.build_release.source_state', return_value={'commit': 'a' * 40, 'dirty': True}):
            with self.assertRaisesRegex(ValueError, '干净'):
                build_release(destination)
        self.assertFalse(destination.exists())

    def test_packaging_detects_an_engine_that_does_not_match_its_bundle_manifest(self):
        from tools.build_release import make_packages
        def changed(*args):
            packages = make_packages(*args)
            path = packages['tool'] / 'pptx_animation_split/_motion.py'
            path.write_bytes(path.read_bytes() + b'\n')
            return packages
        destination = self.work / 'changed-engine'
        with patch('tools.build_release.make_packages', side_effect=changed), self.assertRaisesRegex(ValueError, '已修改'):
            build_release(destination, local=True)
        self.assertFalse(destination.exists())

    def test_skill_source_contains_the_only_maintained_engine(self):
        names = {path.relative_to(ROOT).as_posix() for path in source_files()}
        self.assertIn('skills/pptx-animation-split/SKILL.md', names)
        self.assertIn('skills/pptx-animation-split/scripts/run.py', names)
        self.assertTrue((ROOT / 'skills/pptx-animation-split/scripts/pptx_animation_split/_core.py').is_file())
        self.assertFalse((ROOT / 'pptx_animation_split/_core.py').exists())
        self.assertEqual([path.name for path in (ROOT / 'pptx_animation_split').glob('*.py')], ['__init__.py'])

    def test_packaging_rejects_plugin_metadata_with_a_different_version(self):
        from tools.build_release import make_packages
        def changed(*args):
            packages = make_packages(*args)
            path = packages['skill'] / 'plugin.json'
            data = json.loads(path.read_text())
            data['version'] = '99.0.0'
            path.write_text(json.dumps(data))
            return packages
        with patch('tools.build_release.make_packages', side_effect=changed), self.assertRaisesRegex(ValueError, '插件清单版本'):
            build_release(self.work / 'mixed-plugin-metadata', local=True)

    def test_direct_project_skill_installation_runs_without_the_plugin_container(self):
        package = self.install('skill')
        installed = self.work / 'project/.agents/skills/pptx-animation-split'
        shutil.copytree(package / 'skills/pptx-animation-split', installed)
        output = self.work / 'direct-skill.pptx'
        result = self.launch(installed / 'scripts/run.py', '--no-update-check', 'split', ROOT / 'examples/demo.pptx', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())


if __name__ == '__main__':
    unittest.main()
