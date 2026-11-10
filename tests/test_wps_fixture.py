from pathlib import Path
import tempfile
import unittest
import zipfile

from pptx_animation_split._core import collect_ns
from pptx_animation_split.operations import split_file
from tests.fixtures import A, P
from tests.test_animation_matrix import object_ids, states


FIXTURE = Path(__file__).resolve().parents[1] / 'examples/animation-cases.pptx'


class WpsExportTests(unittest.TestCase):
    def test_native_entrance_exit_scale_and_curve_combinations(self):
        with zipfile.ZipFile(FIXTURE) as archive:
            self.assertIn('dcterms', collect_ns(archive.read('docProps/core.xml')))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output.pptx'
            per_slide, notes, total = split_file(FIXTURE, output, log=lambda _: None)
            self.assertEqual(notes, [])
            self.assertEqual(total, 13)
            self.assertEqual([count for _, count, _ in per_slide], [2, 2, 4, 4, 1])
            pages = states(output)
            expected = [set(), {'3', '4', '5'}, {'3', '4', '5'}, {'3', '4', '5'}, {'3', '4', '5'}, {'4', '5'}, {'5'}, set(), {'3', '4', '5'}, {'3', '4', '5'}, {'3', '4', '5'}, {'3', '4', '5'}, {'3', '4', '5'}]
            for index, (page, visible) in enumerate(zip(pages, expected)):
                with self.subTest(page=index + 1):
                    self.assertEqual(object_ids(page) & {'3', '4', '5'}, visible)
            scaled = next(shape for shape in pages[3].iter(P + 'sp') if shape.find(P + 'nvSpPr/' + P + 'cNvPr').get('id') == '3')
            self.assertEqual({node.get('sz') for node in scaled.iter(A + 'defRPr')}, {'3300'})
            transform = scaled.find(P + 'spPr/' + A + 'xfrm')
            self.assertEqual(transform.find(A + 'off').attrib, {'x': '-45720', 'y': '1600200'})
            moved = next(shape for shape in pages[11].iter(P + 'sp') if shape.find(P + 'nvSpPr/' + P + 'cNvPr').get('id') == '3')
            self.assertEqual(moved.find(P + 'spPr/' + A + 'xfrm/' + A + 'off').attrib, {'x': '1582424', 'y': '2522220'})

    def test_repetition_and_standard_trigger_example_has_eight_states(self):
        source = FIXTURE.parent / 'interaction-repeat-cases.pptx'
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output.pptx'
            per_slide, notes, total = split_file(source, output, log=lambda _: None)
            self.assertEqual(notes, [])
            self.assertEqual(total, 8)
            self.assertEqual([count for _, count, _ in per_slide], [2, 3, 3])
            pages = states(output)
            def width(page, sid):
                for shape in page.iter():
                    nv = next((node for node in shape if node.tag in (P + 'nvSpPr', P + 'nvPicPr')), None)
                    if nv is not None and nv.find(P + 'cNvPr').get('id') == sid:
                        return shape.find(P + 'spPr/' + A + 'xfrm/' + A + 'ext').get('cx')
                self.fail('Missing fixture object ' + sid)
            self.assertEqual(width(pages[1], '4'), '2743200')
            self.assertEqual([width(page, '5') for page in pages[2:5]], ['2194560', '2194560', '3291840'])
            self.assertEqual([width(page, '3') for page in pages[5:]], ['2377440', '2377440', '3566160'])


if __name__ == '__main__':
    unittest.main()
