from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pptx_animation_split.cli import main
from pptx_animation_split.operations import split_file
from pptx_animation_split._core import parse_slide_animation
from pptx_animation_split.verify import verify
from tests.fixtures import A, P, add_interactive, effect, slide, write_deck
from tests.test_animation_matrix import object_ids, states


class InteractionAndRepetitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.counter = 0

    def convert(self, root, route=None):
        self.counter += 1
        source = self.folder / ('source%d.pptx' % self.counter)
        output = self.folder / ('output%d.pptx' % self.counter)
        write_deck(source, [root])
        orders = {'ppt/slides/slide1.xml': route} if route is not None else None
        split_file(source, output, log=lambda _: None, click_orders=orders)
        self.assertEqual(verify(source, output, log=lambda _: None, click_orders=orders), [])
        return states(output)

    def test_default_order_keeps_main_clicks_then_each_trigger(self):
        root = slide([(2, 'text'), (3, 'picture'), (4, 'shape'), (5, 'group')], [effect(3), effect(3, 'exit')])
        add_interactive(root, 4, [effect(2), effect(3, trigger='afterEffect', delay=250)])
        add_interactive(root, 5, [effect(4, 'exit')])
        output = self.convert(root)
        expected = [{'4', '5'}, {'3', '4', '5'}, {'4', '5'}, {'2', '3', '4', '5'}, {'2', '3', '5'}]
        self.assertEqual([object_ids(page) & {'2', '3', '4', '5'} for page in output], expected)

    def test_interactive_only_entrance_on_each_object_type(self):
        for kind in ('text', 'picture', 'shape', 'group'):
            with self.subTest(kind=kind):
                root = slide([(2, kind), (4, 'shape')])
                add_interactive(root, 4, [effect(2)])
                output = self.convert(root)
                self.assertEqual(['2' in object_ids(page) for page in output], [False, True])

    def test_one_trigger_can_advance_multiple_click_groups(self):
        root = slide([(2, 'text'), (3, 'picture'), (4, 'shape')])
        add_interactive(root, 4, [effect(2), effect(3), effect(2, 'exit')])
        output = self.convert(root)
        self.assertEqual([object_ids(page) & {'2', '3'} for page in output], [set(), {'2'}, {'2', '3'}, {'3'}])

    def test_one_object_click_starts_two_linked_sequences_together(self):
        root = slide([(2, 'text'), (3, 'picture'), (4, 'shape')])
        add_interactive(root, 4, [effect(2)])
        add_interactive(root, 4, [effect(3, delay=500)])
        output = self.convert(root)
        self.assertEqual(len(output), 2)
        self.assertEqual(object_ids(output[-1]) & {'2', '3'}, {'2', '3'})

    def test_optional_time_ids_do_not_merge_distinct_triggered_transforms(self):
        root = slide([(2, 'picture'), (3, 'shape'), (4, 'shape')])
        add_interactive(root, 4, [effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000)), effect(3, 'emph', trigger='withEffect', attributes={'by': '5400000'})])
        for node in root.iter(P + 'cTn'):
            node.attrib.pop('id', None)
        before = ET.tostring(root)
        output = self.convert(root)
        self.assertEqual(ET.tostring(root), before)
        self.assertEqual(output[-1].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm/' + A + 'ext').get('cx'), '3000000')
        shape = next(n for n in output[-1].iter(P + 'sp') if n.find(P + 'nvSpPr/' + P + 'cNvPr').get('id') == '3')
        self.assertEqual(shape.find(P + 'spPr/' + A + 'xfrm').get('rot'), '5400000')

    def test_custom_route_changes_the_result_and_keeps_unplayed_entrances_hidden(self):
        root = slide([(2, 'text'), (3, 'picture'), (4, 'shape'), (5, 'shape')])
        add_interactive(root, 4, [effect(2), effect(3, trigger='afterEffect')])
        add_interactive(root, 5, [effect(2, 'exit')])
        default = self.convert(root)
        reversed_route = self.convert(root, ['shape:5', 'shape:4'])
        no_clicks = self.convert(root, [])
        self.assertNotIn('2', object_ids(default[-1]))
        self.assertIn('2', object_ids(reversed_route[-1]))
        self.assertEqual(object_ids(no_clicks[0]) & {'2', '3'}, set())

    def test_hidden_trigger_or_hidden_parent_requires_a_different_route(self):
        for target in (4, 104):
            with self.subTest(trigger=target):
                root = slide([(2, 'text'), (4, 'group')], [effect(4, 'exit')])
                add_interactive(root, target, [effect(2)])
                with self.assertRaisesRegex(ValueError, '不可见'):
                    self.convert(root)
                output = self.convert(root, ['shape:' + str(target), 'next'])
                self.assertEqual(['2' in object_ids(page) for page in output], [False, True, True])

    def test_retriggering_replaces_the_same_frozen_scale_instead_of_multiplying_it(self):
        for restart in ('whenNotActive', 'never'):
            with self.subTest(restart=restart):
                root = slide([(2, 'picture'), (4, 'shape')])
                add_interactive(root, 4, [effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000))], restart=restart)
                output = self.convert(root, ['shape:4', 'shape:4'])
                sizes = [page.find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm/' + A + 'ext').get('cx') for page in output]
                self.assertEqual(sizes, ['2000000', '3000000', '3000000'])

    def test_unknown_or_ambiguous_trigger_refuses_output(self):
        for mode in ('missing_shape', 'two_targets', 'different_next', 'unassigned_behavior'):
            with self.subTest(mode=mode):
                root = slide([(2, 'text'), (4, 'shape')])
                channel = add_interactive(root, 999 if mode == 'missing_shape' else 4, [effect(2)])
                if mode == 'two_targets':
                    cond = ET.SubElement(channel.find(P + 'stCondLst'), P + 'cond', evt='onClick', delay='0')
                    ET.SubElement(ET.SubElement(cond, P + 'tgtEl'), P + 'spTgt', spid='2')
                elif mode == 'different_next':
                    parents = {child: parent for parent in root.iter() for child in parent}
                    parents[channel].find(P + 'nextCondLst/' + P + 'cond/' + P + 'tgtEl/' + P + 'spTgt').set('spid', '2')
                elif mode == 'unassigned_behavior':
                    ET.SubElement(root.find(P + 'timing'), P + 'cmd', type='call', cmd='unknown')
                with self.assertRaisesRegex(ValueError, '未支持'):
                    self.convert(root)
                self.assertFalse((self.folder / ('output%d.pptx' % self.counter)).exists())

    def test_custom_route_does_not_bypass_time_modifiers_outside_sequences(self):
        for mode in ('reverse_speed', 'reverse', 'repeat', 'early_end'):
            with self.subTest(mode=mode):
                root = slide([(2, 'text')], [effect(2)])
                parent = next(node for node in root.iter(P + 'cTn') if node.get('nodeType') == 'tmRoot')
                if mode == 'reverse_speed':
                    parent.set('spd', '-100000')
                elif mode == 'reverse':
                    parent.set('autoRev', '1')
                elif mode == 'repeat':
                    parent.set('repeatCount', '3000')
                else:
                    condition = ET.SubElement(ET.SubElement(parent, P + 'endCondLst'), P + 'cond', delay='100')
                with self.assertRaisesRegex(ValueError, '未支持'):
                    self.convert(root, ['next'])

    def test_custom_order_cli_round_trip_and_invalid_routes(self):
        source, output = self.folder / '源.pptx', self.folder / '结果.pptx'
        root = slide([(2, 'text'), (4, 'shape'), (5, 'shape')])
        add_interactive(root, 4, [effect(2)])
        add_interactive(root, 5, [effect(2, 'exit')])
        write_deck(source, [root])
        plan = self.folder / '点击.json'
        plan.write_text(json.dumps({'1': ['shape:5', 'shape:4']}))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['split', str(source), str(output), '--click-order', str(plan)]), 0)
            self.assertEqual(main(['verify', str(source), str(output), '--click-order', str(plan)]), 0)
            self.assertEqual(main(['verify', str(source), str(output)]), 1)
        for index, content in enumerate(({'2': []}, {'1': [7]}, {'1': ['next']}, {'1': ['shape:999']}, {'1': ['wrong']}, {'1': [], '01': []}, [])):
            plan.write_text(json.dumps(content))
            destination = self.folder / ('invalid%d.pptx' % index)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(main(['split', str(source), str(destination), '--click-order', str(plan)]), 1)
            self.assertFalse(destination.exists())
        write_deck(source, [slide([(2, 'text')])])
        plan.write_text(json.dumps({'1': ['next']}))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['split', str(source), str(self.folder / 'static-invalid.pptx'), '--click-order', str(plan)]), 1)

    def test_whole_repeat_counts_keep_one_state_per_click_and_do_not_accumulate_scale(self):
        for kind in ('text', 'picture', 'shape', 'group'):
            for count in (2000, 3000, 10000, 1000000):
                with self.subTest(kind=kind, count=count):
                    root = slide([(2, kind)], [effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000), timing={'repeatCount': str(count)})])
                    output = self.convert(root)
                    self.assertEqual(len(output), 2)
                    props = P + ('grpSpPr' if kind == 'group' else 'spPr')
                    transform = output[-1].find('.//' + props + '/' + A + 'xfrm')
                    self.assertEqual(transform.find(A + 'ext').get('cx'), '3000000')

    def test_last_repeated_entrance_is_ordered_after_an_earlier_exit(self):
        for repeat in ({'repeatCount': '3000'}, {'repeatDur': '1500'}):
            with self.subTest(repeat=repeat):
                root = slide([(2, 'picture')], [effect(2, duration=500, timing=repeat), effect(2, 'exit', trigger='withEffect', delay=500, duration=100)])
                output = self.convert(root)
                self.assertEqual(['2' in object_ids(page) for page in output], [False, True])

    def test_repeated_exit_finishes_after_a_delayed_reentry(self):
        root = slide([(2, 'shape')], [effect(2, 'exit', duration=500, timing={'repeatCount': '3000'}), effect(2, trigger='withEffect', delay=900, duration=100)])
        output = self.convert(root)
        self.assertEqual(['2' in object_ids(page) for page in output], [True, False])

    def test_repeated_container_keeps_the_last_cycle_visibility_order(self):
        root = slide([(2, 'text')], [effect(2, duration=500), effect(2, 'exit', trigger='afterEffect', duration=100)])
        main = next(n for n in root.iter(P + 'cTn') if n.get('nodeType') == 'mainSeq')
        main.find(P + 'childTnLst/' + P + 'par/' + P + 'cTn').set('repeatCount', '3000')
        output = self.convert(root)
        self.assertEqual(['2' in object_ids(page) for page in output], [False, False])

    def test_loop_until_next_click_has_a_bounded_representative_state(self):
        root = slide([(2, 'picture'), (3, 'shape')], [effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000), timing={'repeatCount': 'indefinite'}), effect(3)])
        loop = next(n for n in root.iter(P + 'cTn') if n.get('repeatCount'))
        cond = ET.SubElement(ET.SubElement(loop, P + 'endCondLst'), P + 'cond', evt='onNext')
        ET.SubElement(ET.SubElement(cond, P + 'tgtEl'), P + 'sldTgt')
        groups, notes = parse_slide_animation(root)
        self.assertEqual(notes, [])
        self.assertTrue(any('代表状态' in message for message in groups.info))
        output = self.convert(root)
        self.assertEqual(len(output), 3)
        self.assertEqual(['3' in object_ids(page) for page in output], [False, False, True])

    def test_loop_until_slide_end_and_auto_reverse_have_bounded_states(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                timing = {'repeatCount': 'indefinite', 'autoRev': '1' if reverse else '0'}
                root = slide([(2, 'picture')], [effect(2, 'emph', behavior='animScale', attributes={}, scale=(150000, 150000), timing=timing)])
                loop = next(n for n in root.iter(P + 'cTn') if n.get('repeatCount'))
                cond = ET.SubElement(ET.SubElement(loop, P + 'endCondLst'), P + 'cond', evt='onEnd')
                ET.SubElement(cond, P + 'tn', val='1')
                output = self.convert(root)
                self.assertEqual(len(output), 2)
                extent = output[-1].find('.//' + P + 'pic/' + P + 'spPr/' + A + 'xfrm/' + A + 'ext')
                self.assertEqual(extent.get('cx'), '2000000' if reverse else '3000000')

    def test_partial_or_unknown_repetition_remains_an_explicit_error(self):
        for attributes in ({'repeatCount': '1500'}, {'repeatDur': '750'}, {'repeatCount': 'invalid'}, {'repeatCount': '0'}, {'repeatCount': 'indefinite', 'fill': 'remove'}):
            with self.subTest(timing=attributes):
                root = slide([(2, 'picture')], [effect(2, 'emph', timing=attributes, duration=500)])
                with self.assertRaisesRegex(ValueError, '未支持'):
                    self.convert(root)

    def test_infinite_repetition_does_not_hide_a_later_overlapping_animation(self):
        for cls in ('emph', 'entr'):
            with self.subTest(cls=cls):
                second_class = 'emph' if cls == 'emph' else 'exit'
                root = slide([(2, 'picture')], [effect(2, cls, duration=500, timing={'repeatCount': 'indefinite'}), effect(2, second_class, trigger='afterEffect', delay=2000, duration=100)])
                with self.assertRaisesRegex(ValueError, '重叠'):
                    self.convert(root)

    def test_after_effect_does_not_treat_an_infinite_end_event_as_a_finite_wait(self):
        root = slide([(2, 'picture'), (3, 'shape')], [effect(2, 'emph', timing={'repeatCount': 'indefinite'}), effect(3, trigger='afterEffect')])
        effects = [node for node in root.iter(P + 'cTn') if node.get('presetID')]
        parents = {child: parent for parent in root.iter() for child in parent}
        wrapper = parents[parents[parents[effects[1]]]]
        condition = wrapper.find(P + 'stCondLst/' + P + 'cond')
        condition.set('delay', '0')
        condition.set('evt', 'onEnd')
        ET.SubElement(condition, P + 'tn', val=effects[0].get('id'))
        with self.assertRaisesRegex(ValueError, '无限循环的结束事件'):
            self.convert(root)


if __name__ == '__main__':
    unittest.main()
