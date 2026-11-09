from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pptx_animation_split._motion import motion_endpoint
from pptx_animation_split.operations import split_file
from tests.fixtures import A, P, effect, slide, write_deck
from tests.test_animation_matrix import states, object_ids


class PathEndpointTests(unittest.TestCase):
    def test_absolute_relative_cubic_and_closed_paths(self):
        paths = [
            ('M 0 0 L 0.2 -0.25 E', (0.2, -0.25)),
            ('M 0.1 0.2 L 0.4 0.6', (0.4, 0.6)),
            ('M 0.1 0.2 l 0.2 0.3 l 0.1 -0.2', (0.4, 0.3)),
            ('M 0 0 C 0.1 0.1 0.2 0.3 0.4 0.5', (0.4, 0.5)),
            ('M 0.1 0.2 c 0.1 0.1 0.2 0.3 0.4 0.5', (0.5, 0.7)),
            ('M 0 0 L 1 0 L 1 1 L 0 1 Z E', (0, 0)),
            ('M 0.1 0.2 C 0.2 0.3 0.4 0.5 0.6 0.7 z', (0.1, 0.2)),
            ('M 0 0 C 0.1 0.2 0.3 0.4 0.5 0.6 L 0.7 0.8', (0.7, 0.8)),
            ('M 0 0 L 2e-1 -2.5e-1', (0.2, -0.25)),
        ]
        for path, expected in paths:
            with self.subTest(path=path):
                actual = motion_endpoint(path)
                self.assertIsNotNone(actual)
                self.assertAlmostEqual(actual[0], expected[0])
                self.assertAlmostEqual(actual[1], expected[1])

    def test_formulas_unknown_commands_and_malformed_paths_are_rejected(self):
        for path in ('', 'M 0 0 Q 1 1 2 2', 'M 0 0 L (1/2) 0', 'M 0 0 L .2 .3', 'M 0 0 L 1e999 0', 'M 0 0 C 1 2', 'M 0 0 L 1 2 3', 'L 0 0', 'M 0 0 ; L 1 1'):
            with self.subTest(path=path):
                self.assertIsNone(motion_endpoint(path))


class CompoundGeometryTests(unittest.TestCase):
    def convert(self, events, kind='picture'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = Path(directory.name) / 'source.pptx'
        output = Path(directory.name) / 'output.pptx'
        write_deck(source, [slide([(2, kind)], events)])
        split_file(source, output, log=lambda _: None)
        return states(output)

    def motion(self, path, **options):
        return effect(2, 'path', behavior='animMotion', attributes={'origin': 'layout', 'path': path}, **options)

    def test_successive_motion_paths_use_original_layout_anchor(self):
        output = self.convert([self.motion('M 0 0 L 0.1 0.1'), self.motion('M 0.1 0.1 C 0.2 0.1 0.2 0.2 0.3 0.2')])
        transform = output[2].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm')
        self.assertEqual(transform.find(A + 'off').get('x'), '3743200')
        self.assertEqual(transform.find(A + 'off').get('y'), '2371600')

    def test_closed_path_can_leave_identical_static_states(self):
        output = self.convert([self.motion('M 0 0 L 0.1 0 C 0.1 0.2 0 0.2 0 0 Z')])
        self.assertEqual(len(output), 2)
        transform = output[1].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm')
        self.assertEqual(transform.find(A + 'off').attrib, {'x': '1000000', 'y': '1000000'})

    def test_scale_rotate_and_translate_on_one_click_preserve_picture_crop(self):
        events = [effect(2, 'emph', behavior='animScale', attributes={}, scale=(50000, 50000)), effect(2, 'emph', trigger='withEffect', attributes={'by': '5400000'}), self.motion('M 0 0 C 0.1 0.2 0.3 0.4 0.2 0.1', trigger='afterEffect')]
        output = self.convert(events)
        self.assertEqual(len(output), 2)
        picture = output[1].find('.//' + P + 'pic')
        transform = picture.find(P + 'spPr/' + A + 'xfrm')
        self.assertEqual(transform.find(A + 'ext').attrib, {'cx': '1000000', 'cy': '500000'})
        self.assertEqual(transform.find(A + 'off').attrib, {'x': '3328800', 'y': '1935800'})
        self.assertEqual(transform.get('rot'), '5400000')
        self.assertEqual(picture.find(P + 'blipFill/' + A + 'srcRect').attrib, {'l': '10000', 'r': '20000'})

    def test_shape_and_uniform_explicit_text_scale_keep_center(self):
        for kind in ('shape', 'text', 'group'):
            with self.subTest(kind=kind):
                output = self.convert([effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000))], kind)
                props = P + ('grpSpPr' if kind == 'group' else 'spPr')
                transform = output[1].find('.//' + props + '/' + A + 'xfrm')
                self.assertEqual(transform.find(A + 'off').attrib, {'x': '500000', 'y': '750000'})
                self.assertEqual(transform.find(A + 'ext').attrib, {'cx': '3000000', 'cy': '1500000'})
                if kind in ('text', 'group'):
                    self.assertEqual({n.get('sz') for n in output[1].iter(A + 'rPr')}, {'3000'})

    def test_delayed_entrance_after_short_exit_finishes_visible(self):
        events = [effect(2, delay=1200, duration=100), effect(2, 'exit', trigger='withEffect', duration=300)]
        output = self.convert(events)
        self.assertEqual(['2' in object_ids(page) for page in output], [False, True])

    def test_overlapping_animations_on_same_property_are_explicitly_rejected(self):
        with self.assertRaisesRegex(ValueError, '重叠'):
            self.convert([effect(2, 'emph', duration=1000), effect(2, 'emph', trigger='withEffect', delay=200, duration=1000)])

    def test_nonuniform_text_scale_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '未支持'):
            self.convert([effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 100000))], 'text')

    def test_formula_or_paragraph_geometry_is_rejected_without_moving_the_whole_box(self):
        for mode in ('formula_scale', 'paragraph_rotation', 'paragraph_motion'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                if mode == 'formula_scale':
                    event = effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000))
                elif mode == 'paragraph_rotation':
                    event = effect(2, 'emph', paragraphs=(1, 1))
                else:
                    event = self.motion('M 0 0 L 0.1 0.1', paragraphs=(1, 1))
                root = slide([(2, 'text')], [event])
                if mode == 'formula_scale':
                    math = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
                    ET.SubElement(root.find('.//' + P + 'txBody/' + A + 'p'), math + 'oMath')
                source, output = Path(temporary) / 'source.pptx', Path(temporary) / 'output.pptx'
                write_deck(source, [root])
                with self.assertRaisesRegex(ValueError, '未支持'):
                    split_file(source, output, log=lambda _: None)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
