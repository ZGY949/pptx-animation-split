from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from pptx_animation_split import __version__
from pptx_animation_split.bundle import file_hashes, verify_bundle
from tools.package_source import source_files
from tools.sync_skill import SKILL_RELATIVE, sync_skill


ROOT = Path(__file__).resolve().parents[1]


class SkillDistributionTests(unittest.TestCase):
    def test_source_inventory_includes_every_required_skill_file(self):
        inventory = {path.relative_to(ROOT).as_posix() for path in source_files()}
        manifest = verify_bundle(ROOT / SKILL_RELATIVE)
        required = {(SKILL_RELATIVE / name).as_posix() for name in manifest['files']}
        required.add((SKILL_RELATIVE / 'bundle.json').as_posix())
        self.assertEqual(required - inventory, set())

    def test_source_skill_runs_after_copying_only_its_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            installed = work / '.agents/skills/pptx-animation-split'
            shutil.copytree(ROOT / SKILL_RELATIVE, installed, ignore=shutil.ignore_patterns('__pycache__'))
            before = file_hashes(installed)
            launcher = installed / 'scripts/run.py'
            source = ROOT / 'examples/demo.pptx'
            output = work / 'static.pptx'
            for arguments in (['--no-update-check', 'split', source, output], ['verify', source, output]):
                result = subprocess.run([sys.executable, '-I', '-B', str(launcher), *map(str, arguments)], cwd=work, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(file_hashes(installed), before)
            self.assertEqual(verify_bundle(installed)['version'], __version__)

    def test_sync_check_is_read_only_and_repair_restores_generated_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary)
            for source in source_files():
                destination = snapshot / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            reference = snapshot / SKILL_RELATIVE / 'references/LIMITATIONS.md'
            original = reference.read_bytes()
            reference.write_bytes(original + b'\n')
            with self.assertRaisesRegex(ValueError, '未同步'):
                sync_skill(snapshot, check=True)
            self.assertEqual(reference.read_bytes(), original + b'\n')
            sync_skill(snapshot)
            self.assertEqual(reference.read_bytes(), original)
            self.assertEqual(sync_skill(snapshot, check=True), [])
            self.assertEqual(verify_bundle(snapshot / SKILL_RELATIVE)['version'], __version__)

    def test_original_module_entry_point_still_works_from_source(self):
        result = subprocess.run([sys.executable, '-B', '-m', 'pptx_animation_split', '--version'], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_python_build_metadata_does_not_change_the_distributed_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary)
            for source in source_files():
                destination = snapshot / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            metadata = snapshot / SKILL_RELATIVE / 'scripts/pptx_animation_split.egg-info'
            metadata.mkdir()
            (metadata / 'SOURCES.txt').write_text('generated build metadata\n')
            self.assertEqual(sync_skill(snapshot, check=True), [])
            self.assertFalse(any('.egg-info' in str(path.relative_to(snapshot)) for path in source_files(snapshot)))


if __name__ == '__main__':
    unittest.main()
