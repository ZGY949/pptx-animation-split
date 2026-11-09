from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from pptx_animation_split._core import A, P, slide_order
from pptx_animation_split.cli import main
from pptx_animation_split.operations import split_file


DEMO = Path(__file__).resolve().parents[1] / 'examples' / 'demo.pptx'


def rewrite(source, destination, part, change):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, 'w') as output:
        for item in original.infolist():
            data = original.read(item.filename)
            if item.filename == part:
                root = ET.fromstring(data)
                change(root)
                data = ET.tostring(root)
            output.writestr(item, data)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / '源课件.pptx'
        self.source.write_bytes(DEMO.read_bytes())
        self.destination = self.root / '拆分结果.pptx'

    def run_cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main([str(arg) for arg in args])
        return status, output.getvalue(), errors.getvalue()

    def test_split_preserves_source_and_produces_three_static_states(self):
        digest = hashlib.sha256(self.source.read_bytes()).digest()
        status, _, errors = self.run_cli('split', self.source, self.destination)
        self.assertEqual(status, 0, errors)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), digest)
        self.assertEqual(self.run_cli('verify', self.source, self.destination)[0], 0)
        with zipfile.ZipFile(self.destination) as archive:
            slides = slide_order(archive)
            self.assertEqual(len(slides), 3)
            texts = []
            for name in slides:
                root = ET.fromstring(archive.read(name))
                self.assertIsNone(root.find(P + 'timing'))
                texts.append([node.text for node in root.iter(A + 't')])
            self.assertNotIn('Answer: 42', texts[0])
            self.assertIn('Answer: 42', texts[1])
            self.assertIn('Hint: multiply 6 by 7.', texts[1])
            self.assertNotIn('Hint: multiply 6 by 7.', texts[2])
        self.assertEqual(list(self.root.glob('.pptx-split-*')), [])

    def test_same_path_is_rejected_without_modifying_source(self):
        before = self.source.read_bytes()
        self.assertEqual(self.run_cli('split', self.source, self.source)[0], 1)
        self.assertEqual(self.source.read_bytes(), before)

    def test_existing_output_is_not_overwritten(self):
        self.destination.write_bytes(b'existing result')
        self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertEqual(self.destination.read_bytes(), b'existing result')

    def test_hard_link_to_source_is_rejected(self):
        os.link(self.source, self.destination)
        before = self.source.read_bytes()
        self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertEqual(self.source.read_bytes(), before)

    @unittest.skipIf(os.name == 'nt', 'Windows symlink creation may require elevated permissions')
    def test_symlink_to_source_is_rejected(self):
        self.destination.symlink_to(self.source)
        before = self.source.read_bytes()
        self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertEqual(self.source.read_bytes(), before)

    def test_invalid_zip_does_not_leave_output_or_temporary_files(self):
        self.source.write_bytes(b'not a zip file')
        self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('.pptx-split-*')), [])

    def test_failed_validation_does_not_publish_output(self):
        with patch('pptx_animation_split.operations.verify', return_value=['invalid state']):
            self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob('.pptx-split-*')), [])

    def test_output_created_during_conversion_is_not_overwritten(self):
        def check(*args, **kwargs):
            self.destination.write_bytes(b'created by another process')
            return []
        with patch('pptx_animation_split.operations.verify', side_effect=check):
            self.assertEqual(self.run_cli('split', self.source, self.destination)[0], 1)
        self.assertEqual(self.destination.read_bytes(), b'created by another process')
        self.assertEqual(list(self.root.glob('.pptx-split-*')), [])

    def test_unsupported_effect_is_reported_with_exit_code_three(self):
        def change(root):
            node = next(node for node in root.iter(P + 'cTn') if node.get('presetClass') == 'entr')
            node.set('presetClass', 'emph')
        source = self.root / 'unsupported.pptx'
        rewrite(self.source, source, 'ppt/slides/slide1.xml', change)
        status, _, error = self.run_cli('split', source, self.destination)
        self.assertEqual(status, 1, error)
        self.assertFalse(self.destination.exists())
        status, _, error = self.run_cli('split', source, self.destination, '--allow-partial')
        self.assertEqual(status, 3, error)
        self.assertTrue(self.destination.is_file())
        self.assertEqual(self.run_cli('verify', source, self.destination)[0], 3)

    def test_verify_rejects_an_unsplit_copy(self):
        self.destination.write_bytes(self.source.read_bytes())
        self.assertEqual(self.run_cli('verify', self.source, self.destination)[0], 1)

    def test_peek_uses_presentation_order_instead_of_part_number(self):
        split_file(self.source, self.destination, log=lambda message: None)
        reordered = self.root / 'reordered.pptx'
        def reverse(root):
            order = root.find(P + 'sldIdLst')
            order[:] = reversed(list(order))
        rewrite(self.destination, reordered, 'ppt/presentation.xml', reverse)
        status, output, errors = self.run_cli('peek', reordered, 1)
        self.assertEqual(status, 0, errors)
        self.assertIn('Answer: 42', output)
        self.assertNotIn('Hint: multiply 6 by 7.', output)

    def test_peek_rejects_out_of_range_and_reversed_ranges(self):
        for value in ('0', '2', '2-1', 'bad'):
            with self.subTest(value=value):
                self.assertEqual(self.run_cli('peek', self.source, value)[0], 1)

    def test_missing_file_and_wrong_extension_are_clear_errors(self):
        for source in (self.root / 'missing.pptx', self.root / 'old.ppt'):
            with self.subTest(source=source):
                status, _, error = self.run_cli('split', source, self.destination)
                self.assertEqual(status, 1)
                self.assertIn('错误', error)

    def test_missing_arguments_show_usage(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as context:
            main(['split'])
        self.assertEqual(context.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
