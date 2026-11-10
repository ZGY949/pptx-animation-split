from contextlib import redirect_stderr, redirect_stdout
import io
import itertools
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from pptx_animation_split.cli import main
from pptx_animation_split.operations import split_file
from pptx_animation_split.verify import verify
from tests.fixtures import A, P, PR, R, effect, rewrite, slide, write_deck


def states(path):
    with zipfile.ZipFile(path) as archive:
        pres = ET.fromstring(archive.read('ppt/presentation.xml'))
        rels = {node.get('Id'): node.get('Target') for node in ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))}
        return [ET.fromstring(archive.read('ppt/' + rels[node.get(R + 'id')])) for node in pres.find(P + 'sldIdLst')]


def object_ids(root):
    return {node.get('id') for node in root.iter(P + 'cNvPr')}


class AnimationMatrixTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.counter = 0

    def convert(self, source_slide, **options):
        self.counter += 1
        source = self.root / ('case%d.pptx' % self.counter)
        output = self.root / ('result%d.pptx' % self.counter)
        write_deck(source, [source_slide], **options)
        split_file(source, output, log=lambda _: None)
        return states(output)

    def test_entrance_and_exit_on_text_picture_shape_and_nested_group(self):
        for kind, cls, preset in itertools.product(('text', 'picture', 'shape', 'group'), ('entr', 'exit'), (1, 2, 10, 15, 22, 35, 52)):
            with self.subTest(kind=kind, cls=cls, preset=preset):
                output = self.convert(slide([(2, kind), (9, 'shape')], [effect(2, cls, preset=preset)]))
                self.assertEqual(len(output), 2)
                self.assertEqual('2' in object_ids(output[0]), cls == 'exit')
                self.assertEqual('2' in object_ids(output[1]), cls == 'entr')
                self.assertTrue(all('9' in object_ids(page) for page in output))
                if kind == 'group':
                    for page in output:
                        self.assertEqual('102' in object_ids(page), '2' in object_ids(page))
                        self.assertEqual('202' in object_ids(page), '2' in object_ids(page))

    def test_all_three_object_trigger_combinations_with_delays(self):
        triggers = ('clickEffect', 'withEffect', 'afterEffect')
        for combination in itertools.product(triggers, repeat=3):
            with self.subTest(triggers=combination):
                events = [effect(index + 2, trigger=trigger, delay=(0, 250, 1250)[index], duration=(300, 700, 1100)[index]) for index, trigger in enumerate(combination)]
                output = self.convert(slide([(2, 'text'), (3, 'picture'), (4, 'shape'), (9, 'shape')], events))
                expected = [set()]
                for event in events:
                    if event['trigger'] == 'clickEffect':
                        expected.append(set(expected[-1]))
                    expected[-1].add(event['sid'])
                self.assertEqual(len(output), len(expected))
                for page, visible in zip(output, expected):
                    self.assertEqual(object_ids(page) & {'2', '3', '4'}, visible)
                    self.assertIn('9', object_ids(page))

    def test_exit_reentry_and_exit_same_click_on_each_object_type(self):
        for kind in ('text', 'picture', 'shape', 'group'):
            with self.subTest(kind=kind):
                events = [effect(2, 'exit'), effect(2, trigger='clickEffect'), effect(2, 'exit', trigger='afterEffect', delay=400), effect(2)]
                output = self.convert(slide([(2, kind)], events))
                self.assertEqual(['2' in object_ids(page) for page in output], [True, False, False, True])

    def test_automatic_entrance_is_settled_before_first_click(self):
        output = self.convert(slide([(2, 'text'), (3, 'picture')], [effect(2, trigger='afterEffect', delay=5000), effect(3)]))
        self.assertEqual(len(output), 2)
        self.assertIn('2', object_ids(output[0]))
        self.assertNotIn('3', object_ids(output[0]))
        self.assertIn('3', object_ids(output[1]))

    def test_automatic_rotation_applies_to_initial_state(self):
        output = self.convert(slide([(2, 'picture')], [effect(2, 'emph', trigger='withEffect', attributes={'by': '5400000'})]))
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm').get('rot'), '5400000')

    def test_paragraph_combinations_preserve_all_paragraphs_and_visibility(self):
        events = [effect(2, paragraphs=(1, 1)), effect(2, paragraphs=(2, 2), trigger='afterEffect', delay=1000), effect(2, 'exit', paragraphs=(1, 1))]
        output = self.convert(slide([(2, 'text')], events))
        for page in output:
            paragraphs = page.findall('.//' + P + 'txBody/' + A + 'p')
            self.assertEqual(len(paragraphs), 3)
            self.assertEqual([''.join(node.itertext()) for node in paragraphs], ['题干 / question', 'Answer: 42', 'x² + y² = z²'])
        self.assertIsNone(output[1].find('.//' + P + 'txBody/' + A + 'p[2]/' + A + 'r/' + A + 'rPr/' + A + 'solidFill/' + A + 'srgbClr/' + A + 'alpha'))
        self.assertIsNotNone(output[2].find('.//' + P + 'txBody/' + A + 'p[2]/' + A + 'r/' + A + 'rPr/' + A + 'solidFill/' + A + 'srgbClr/' + A + 'alpha'))

    def test_full_rotation_repeated_on_consecutive_clicks_keeps_both_steps(self):
        output = self.convert(slide([(2, 'picture')], [effect(2, 'emph', attributes={'by': '21600000'}), effect(2, 'emph', attributes={'by': '21600000'})]))
        self.assertEqual(len(output), 3)
        self.assertEqual(output[-1].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm').get('rot'), '0')

    def test_transitions_removed_including_compatibility_wrappers(self):
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                source_slide = slide([(2, 'text')], [effect(2)])
                parent = source_slide
                if wrapped:
                    mc = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
                    alternate = ET.SubElement(source_slide, mc + 'AlternateContent')
                    parent = ET.SubElement(alternate, mc + 'Fallback')
                transition = ET.SubElement(parent, P + 'transition', advClick='0', advTm='1000')
                ET.SubElement(transition, P + 'fade')
                output = self.convert(source_slide)
                self.assertTrue(all(list(page.iter(P + 'transition')) == [] for page in output))

    def test_interactive_or_unidentified_effects_refuse_to_generate_output(self):
        for mode in ('interactive', 'missing_preset', 'invalid_repeat', 'unknown_class'):
            with self.subTest(mode=mode):
                root = slide([(2, 'text')], [effect(2)])
                if mode == 'interactive':
                    next(n for n in root.iter(P + 'cTn') if n.get('nodeType') == 'mainSeq').set('nodeType', 'interactiveSeq')
                node = next(n for n in root.iter(P + 'cTn') if n.get('presetID'))
                if mode == 'missing_preset':
                    del node.attrib['presetID']
                elif mode == 'invalid_repeat':
                    node.set('repeatCount', 'invalid')
                elif mode == 'unknown_class':
                    node.set('presetClass', 'vendor-extension')
                source = self.root / (mode + '.pptx')
                output = self.root / (mode + '-result.pptx')
                write_deck(source, [root])
                with self.assertRaisesRegex(ValueError, '未支持'):
                    split_file(source, output, log=lambda _: None)
                self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob('.pptx-split-*')), [])

    def test_partial_results_require_explicit_flag_and_nonzero_status(self):
        source = self.root / 'source.pptx'
        output = self.root / 'partial.pptx'
        write_deck(source, [slide([(2, 'text')], [effect(2, 'vendor-extension')])])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = main(['split', str(source), str(output), '--allow-partial'])
        self.assertEqual(status, 3)
        self.assertTrue(output.exists())

    def test_empty_wps_time_root_does_not_make_a_static_page_unsupported(self):
        root = slide([(2, 'text')], [effect(2)])
        time_root = next(n for n in root.iter(P + 'cTn') if n.get('nodeType') == 'tmRoot')
        for child in list(time_root):
            time_root.remove(child)
        output = self.convert(root)
        self.assertEqual(len(output), 1)
        self.assertIn('2', object_ids(output[0]))

    def test_exit_then_reentry_can_depend_on_the_previous_effect_end(self):
        root = slide([(2, 'text')], [effect(2, 'exit', duration=300), effect(2, trigger='withEffect')])
        effects = [n for n in root.iter(P + 'cTn') if n.get('presetID')]
        parents = {child: parent for parent in root.iter() for child in parent}
        wrapper = parents[parents[parents[effects[1]]]]
        condition = wrapper.find(P + 'stCondLst/' + P + 'cond')
        condition.set('evt', 'onEnd')
        ET.SubElement(condition, P + 'tn', val=effects[0].get('id'))
        output = self.convert(root)
        self.assertEqual(['2' in object_ids(page) for page in output], [True, True])

    def test_unhandled_time_and_target_structures_refuse_output(self):
        modes = ('partial_wrapper_repeat', 'end_condition', 'speed', 'nested_sequence', 'duplicate_id', 'cyclic_dependency', 'character_range', 'sub_shape', 'missing_target', 'paragraph_range', 'wrapped_timing')
        for mode in modes:
            with self.subTest(mode=mode):
                root = slide([(2, 'text')], [effect(2)])
                time_nodes = list(root.iter(P + 'cTn'))
                target = root.find('.//' + P + 'spTgt')
                if mode == 'partial_wrapper_repeat':
                    time_nodes[2].set('repeatDur', '5100')
                elif mode == 'end_condition':
                    ET.SubElement(ET.SubElement(time_nodes[2], P + 'endCondLst'), P + 'cond', delay='200')
                elif mode == 'speed':
                    time_nodes[2].set('spd', '-100000')
                elif mode == 'nested_sequence':
                    main = next(n for n in time_nodes if n.get('nodeType') == 'mainSeq')
                    ET.SubElement(main.find(P + 'childTnLst'), P + 'seq')
                elif mode == 'duplicate_id':
                    time_nodes[-1].set('id', time_nodes[0].get('id'))
                elif mode == 'cyclic_dependency':
                    condition = root.find('.//' + P + 'stCondLst/' + P + 'cond')
                    condition.set('delay', '0')
                    condition.set('evt', 'onEnd')
                    ET.SubElement(condition, P + 'tn', val=time_nodes[-1].get('id'))
                elif mode == 'character_range':
                    ET.SubElement(ET.SubElement(target, P + 'txEl'), P + 'charRg', st='0', end='2')
                elif mode == 'sub_shape':
                    ET.SubElement(target, P + 'subSp', spid='99')
                elif mode == 'missing_target':
                    target.set('spid', '999')
                elif mode == 'paragraph_range':
                    ET.SubElement(ET.SubElement(target, P + 'txEl'), P + 'pRg', st='1', end='99')
                else:
                    timing = root.find(P + 'timing')
                    root.remove(timing)
                    mc = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
                    ET.SubElement(ET.SubElement(root, mc + 'AlternateContent'), mc + 'Fallback').append(timing)
                source = self.root / (mode + '.pptx')
                output = self.root / (mode + '-output.pptx')
                write_deck(source, [root])
                with self.assertRaisesRegex(ValueError, '未支持'):
                    split_file(source, output, log=lambda _: None)
                self.assertFalse(output.exists())


class NavigationTests(unittest.TestCase):
    def test_links_and_custom_show_follow_reordered_and_expanded_pages(self):
        for names in (None, ['ppt/slides/nested/first.xml', 'ppt/slides/destination.xml']):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source, output = root / 'source.pptx', root / 'output.pptx'
                write_deck(source, [slide([(2, 'text')], [effect(2), effect(2, 'exit')]), slide([(3, 'text')])], names=names, links=[(0, 1), (1, 0)], custom_shows=[(1, 0, 1)])
                split_file(source, output, log=lambda _: None)
                self.assertEqual(verify(source, output, log=lambda _: None), [])
                with zipfile.ZipFile(output) as archive:
                    relation = next(node for node in ET.fromstring(archive.read('ppt/slides/_rels/slide1.xml.rels')) if node.get('Id') == 'jump')
                    self.assertEqual(relation.get('Target'), 'slide4.xml')
                    pres = ET.fromstring(archive.read('ppt/presentation.xml'))
                    refs = {node.get('Id'): node.get('Target') for node in ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))}
                    sequence = [refs[node.get(R + 'id')] for node in pres.findall('.//' + P + 'custShow/' + P + 'sldLst/' + P + 'sld')]
                    self.assertEqual(sequence, ['slides/slide4.xml', 'slides/slide1.xml', 'slides/slide2.xml', 'slides/slide3.xml', 'slides/slide4.xml'])
                broken = root / 'broken.pptx'
                def break_target(relations):
                    next(node for node in relations if node.get('Id') == 'jump').set('Target', 'slide2.xml')
                rewrite(output, broken, 'ppt/slides/_rels/slide1.xml.rels', break_target)
                self.assertTrue(any('跳转' in error for error in verify(source, broken, log=lambda _: None)))


if __name__ == '__main__':
    unittest.main()
