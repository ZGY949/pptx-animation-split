from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from pptx_animation_split._core import A, P, slide_order
from pptx_animation_split.operations import split_file
from pptx_animation_split.verify import shape_index, transparent_paragraph, verify
from tests.fixtures import effect, rewrite, slide, write_deck


class StaticReadingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / 'source.pptx'
        self.output = self.directory / 'output.pptx'

    def split(self, slides, **kwargs):
        write_deck(self.source, slides, **kwargs)
        split_file(self.source, self.output, allow_partial=True, log=lambda _: None)
        self.assertEqual(verify(self.source, self.output, log=lambda _: None), [])
        with zipfile.ZipFile(self.output) as archive:
            return [ET.fromstring(archive.read(name)) for name in slide_order(archive)]

    def visible(self, root):
        return {key[0] for key in shape_index(root)}

    def test_flash_has_visible_and_restored_states_without_revealing_future_objects(self):
        pages = self.split([slide([(2, 'group'), (3, 'text')], [
            effect(2), effect(2, 'exit', 'afterEffect'), effect(3),
        ])])
        self.assertEqual(len(pages), 4)
        self.assertEqual([self.visible(page) for page in pages], [set(), {'2', '102', '202'}, set(), {'3'}])

    def test_simultaneous_arrows_appear_together_before_either_disappears(self):
        pages = self.split([slide([(2, 'text'), (3, 'text')], [
            effect(2), effect(3, trigger='withEffect'),
            effect(2, 'exit', 'afterEffect'), effect(3, 'exit', 'withEffect', delay=500),
        ])])
        self.assertEqual([self.visible(page) for page in pages], [set(), {'2', '3'}, set()])

    def test_flash_paragraph_keeps_placeholder_and_layout(self):
        pages = self.split([slide([(2, 'text')], [
            effect(2, paragraphs=(1, 1)), effect(2, 'exit', 'afterEffect', paragraphs=(1, 1)),
        ])])
        self.assertEqual(len(pages), 3)
        paragraphs = [page.find('.//' + P + 'txBody').findall(A + 'p') for page in pages]
        self.assertEqual([len(items) for items in paragraphs], [3, 3, 3])
        self.assertEqual([transparent_paragraph(items[1]) for items in paragraphs], [True, False, True])
        self.assertEqual([items[1].find('.//' + A + 't').text for items in paragraphs], ['Answer: 42'] * 3)

    def test_simultaneous_exits_stay_together_with_interleaved_media_control(self):
        pages = self.split([slide([(2, 'text'), (3, 'text'), (4, 'text')], [
            effect(2), effect(3, trigger='withEffect'), effect(2, 'exit', 'afterEffect'),
            effect(4, 'mediacall', 'withEffect', delay=500), effect(3, 'exit', 'withEffect', delay=500),
        ])])
        self.assertEqual([self.visible(page) for page in pages], [{'4'}, {'2', '3', '4'}, {'4'}])

    def test_media_only_steps_merge_without_merging_distinct_source_slides_or_links(self):
        media = slide([(2, 'text')], [effect(2, 'mediacall'), effect(2, 'mediacall')])
        pages = self.split([media, slide([(2, 'text')])], links=[(0, 1)], custom_shows=[(0, 1, 0)])
        self.assertEqual(len(pages), 2)
        self.assertEqual([self.visible(page) for page in pages], [{'2'}, {'2'}])

    def test_mixed_media_and_visual_click_keeps_new_content(self):
        pages = self.split([slide([(2, 'text'), (3, 'text')], [
            effect(2, 'mediacall'), effect(3, trigger='withEffect'),
        ])])
        self.assertEqual([self.visible(page) for page in pages], [{'2'}, {'2', '3'}])

    def test_initial_automatic_flash_is_preserved(self):
        pages = self.split([slide([(2, 'text')], [effect(2, trigger='withEffect'), effect(2, 'exit', 'afterEffect')])])
        self.assertEqual([self.visible(page) for page in pages], [{'2'}, set()])

    def test_zero_duration_entry_and_exit_do_not_invent_a_visible_interval(self):
        pages = self.split([slide([(2, 'text')], [effect(2, duration=0), effect(2, 'exit', 'afterEffect', duration=0)])])
        self.assertEqual([self.visible(page) for page in pages], [set(), set()])

    def test_validator_rejects_lost_flash_even_when_final_state_is_correct(self):
        self.split([slide([(2, 'text')], [effect(2), effect(2, 'exit', 'afterEffect')])])
        corrupt = self.directory / 'missing-flash.pptx'

        def hide(root):
            tree = root.find(P + 'cSld/' + P + 'spTree')
            tree.remove(tree.find(P + 'sp'))

        rewrite(self.output, corrupt, 'ppt/slides/slide2.xml', hide)
        errors = verify(self.source, corrupt, log=lambda _: None)
        self.assertTrue(any('应显示但缺失' in error for error in errors), errors)
