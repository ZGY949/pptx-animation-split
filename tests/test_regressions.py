import unittest
import io
import zipfile
import xml.etree.ElementTree as ET

from pptx_animation_split._core import A, MC, P, PR, R, VML, clone_and_render, collect_ns, filter_legacy_drawings, parse_slide_animation, serialize
from pptx_animation_split.verify import check_legacy_state, check_state, shape_index, signature, transient_visibility_step, transparent_paragraph


def effect(sid, paragraphs=None):
    return {'cls': 'entr', 'spid': sid, 'prg': paragraphs}


def textbox(sid):
    element = ET.Element(P + 'sp')
    nv = ET.SubElement(element, P + 'nvSpPr')
    ET.SubElement(nv, P + 'cNvPr', id=sid)
    props = ET.SubElement(element, P + 'spPr')
    transform = ET.SubElement(props, A + 'xfrm')
    ET.SubElement(transform, A + 'off', x='1000', y='2000')
    body = ET.SubElement(element, P + 'txBody')
    ET.SubElement(body, A + 'bodyPr', anchor='ctr')
    for text in ('题干', '第一问', '第二问'):
        paragraph = ET.SubElement(body, A + 'p')
        run = ET.SubElement(paragraph, A + 'r')
        props = ET.SubElement(run, A + 'rPr', sz='2000', b='1')
        ET.SubElement(props, A + 'latin', typeface='Times New Roman')
        ET.SubElement(run, A + 't').text = text
    return element


def slide():
    root = ET.Element(P + 'sld')
    content = ET.SubElement(root, P + 'cSld')
    return root, ET.SubElement(content, P + 'spTree')


def legacy_fixture():
    root, tree = slide()
    relations = ET.Element('{' + PR + '}Relationships')
    ET.SubElement(relations, '{' + PR + '}Relationship', Id='drawing', Type='example/vmlDrawing', Target='../drawings/vmlDrawing1.vml')
    drawing = ET.Element('xml')
    for sid in ('1', '2'):
        frame = ET.SubElement(tree, P + 'graphicFrame')
        nv = ET.SubElement(frame, P + 'nvGraphicFramePr')
        ET.SubElement(nv, P + 'cNvPr', id=sid)
        graphic = ET.SubElement(frame, A + 'graphic')
        data = ET.SubElement(graphic, A + 'graphicData')
        ET.SubElement(data, P + 'oleObj', {'spid': '_shape' + sid, R + 'id': 'ole' + sid})
        ET.SubElement(drawing, VML + 'shape', id='_shape' + sid, style='left:%spt;top:2pt' % sid)
        ET.SubElement(relations, '{' + PR + '}Relationship', Id='ole' + sid, Type='example/oleObject', Target='../embeddings/ole%s.bin' % sid)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('ppt/drawings/vmlDrawing1.vml', ET.tostring(drawing))
        archive.writestr('ppt/drawings/_rels/vmlDrawing1.vml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships" />')
        archive.writestr('ppt/slides/_rels/slide1.xml.rels', ET.tostring(relations))
    buffer.seek(0)
    return root, relations, buffer


class AnimationRegressionTests(unittest.TestCase):
    def test_same_click_entry_then_exit_can_have_an_identical_final_state(self):
        entering = effect('2')
        leaving = dict(entering, cls='exit')
        self.assertTrue(transient_visibility_step([[entering, leaving]], 0))
        self.assertFalse(transient_visibility_step([[entering]], 0))
        self.assertFalse(transient_visibility_step([[entering], [entering, leaving]], 1))
        moving = dict(entering, cls='path', changes=[{'kind': 'translation', 'x': .1, 'y': 0}])
        self.assertFalse(transient_visibility_step([[entering, leaving, moving]], 0))
        root, tree = slide()
        tree.append(textbox('2'))
        hidden = clone_and_render(ET.tostring(root), [[entering, leaving]], 0)
        self.assertEqual(check_state(root, hidden, [[entering, leaving]], 0), [])
        self.assertTrue(check_state(root, hidden, [[entering]], 0))

    def test_both_formula_branches_wait_for_their_click(self):
        root, tree = slide()
        alternate = ET.SubElement(tree, MC + 'AlternateContent')
        for tag in ('Choice', 'Fallback'):
            branch = ET.SubElement(alternate, MC + tag)
            branch.append(textbox('7'))
        groups = [[effect('7')]]
        hidden = clone_and_render(ET.tostring(root), groups, -1)
        visible = clone_and_render(ET.tostring(root), groups, 0)
        self.assertEqual(len(shape_index(hidden)), 0)
        self.assertEqual(len(shape_index(visible)), 2)
        self.assertEqual(check_state(root, hidden, groups, -1), [])
        self.assertEqual(check_state(root, visible, groups, 0), [])
        self.assertTrue(check_state(root, root, groups, -1))

    def test_centered_text_keeps_paragraphs_and_frame_position(self):
        root, tree = slide()
        text = textbox('2')
        tree.append(text)
        tree.append(textbox('9'))
        groups = [[effect('2', (2, 2))]]
        output = clone_and_render(ET.tostring(root), groups, -1)
        original_text = shape_index(root)[('2', ())][0]
        actual_text = shape_index(output)[('2', ())][0]
        self.assertEqual(signature(original_text.find(P + 'spPr')), signature(actual_text.find(P + 'spPr')))
        self.assertEqual(signature(original_text.find(P + 'txBody/' + A + 'bodyPr')), signature(actual_text.find(P + 'txBody/' + A + 'bodyPr')))
        paragraphs = actual_text.findall(P + 'txBody/' + A + 'p')
        self.assertEqual(len(paragraphs), 3)
        self.assertTrue(transparent_paragraph(paragraphs[2]))
        self.assertEqual(signature(shape_index(root)[('9', ())][0]), signature(shape_index(output)[('9', ())][0]))
        self.assertEqual(check_state(root, output, groups, -1), [])
        actual_text.find(P + 'txBody').remove(paragraphs[2])
        self.assertTrue(check_state(root, output, groups, -1))

    def test_revealed_paragraph_restores_original_formula_and_font(self):
        root, tree = slide()
        tree.append(textbox('2'))
        groups = [[effect('2', (2, 2))]]
        output = clone_and_render(ET.tostring(root), groups, 0)
        self.assertEqual(signature(root), signature(output))
        self.assertEqual(check_state(root, output, groups, 0), [])

    def test_animated_group_hides_its_descendants(self):
        root, tree = slide()
        group = ET.SubElement(tree, P + 'grpSp')
        nv = ET.SubElement(group, P + 'nvGrpSpPr')
        ET.SubElement(nv, P + 'cNvPr', id='4')
        group.append(textbox('7'))
        groups = [[effect('4')]]
        output = clone_and_render(ET.tostring(root), groups, -1)
        self.assertEqual(check_state(root, output, groups, -1), [])
        self.assertEqual(len(shape_index(output)), 0)

    def test_exit_and_reentry_follow_the_latest_event(self):
        root, tree = slide()
        tree.append(textbox('2'))
        leaving = effect('2')
        leaving['cls'] = 'exit'
        groups = [[leaving], [effect('2')]]
        for step, count in [(-1, 1), (0, 0), (1, 1)]:
            output = clone_and_render(ET.tostring(root), groups, step)
            self.assertEqual(len(shape_index(output)), count)
            self.assertEqual(check_state(root, output, groups, step), [])

    def test_paragraph_exit_keeps_layout(self):
        root, tree = slide()
        tree.append(textbox('2'))
        leaving = effect('2', (1, 1))
        leaving['cls'] = 'exit'
        output = clone_and_render(ET.tostring(root), [[leaving]], 0)
        paragraphs = shape_index(output)[('2', ())][0].findall(P + 'txBody/' + A + 'p')
        self.assertEqual(len(paragraphs), 3)
        self.assertTrue(transparent_paragraph(paragraphs[1]))
        self.assertEqual(check_state(root, output, [[leaving]], 0), [])

    def test_rotation_changes_angle_only_after_its_click(self):
        root, tree = slide()
        tree.append(textbox('2'))
        rotating = effect('2')
        rotating.update(cls='emph', changes=[{'kind': 'rotation', 'by': 10800000}])
        initial = clone_and_render(ET.tostring(root), [[rotating]], -1)
        output = clone_and_render(ET.tostring(root), [[rotating]], 0)
        before = shape_index(initial)[('2', ())][0].find(P + 'spPr/' + A + 'xfrm')
        after = shape_index(output)[('2', ())][0].find(P + 'spPr/' + A + 'xfrm')
        self.assertIsNone(before.get('rot'))
        self.assertEqual(after.get('rot'), '10800000')
        self.assertEqual(signature(before.find(A + 'off')), signature(after.find(A + 'off')))

    def test_color_changes_keep_text_and_font(self):
        root, tree = slide()
        tree.append(textbox('2'))
        coloring = effect('2')
        coloring.update(cls='emph', changes=[{'kind': 'fontcolor', 'color': '<a:srgbClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="FFFFFF" />'}])
        output = clone_and_render(ET.tostring(root), [[coloring]], 0)
        actual = shape_index(output)[('2', ())][0]
        for props in actual.iter(A + 'rPr'):
            self.assertEqual(props.find(A + 'solidFill/' + A + 'srgbClr').get('val'), 'FFFFFF')
            self.assertEqual(props.get('sz'), '2000')
            self.assertEqual(props.find(A + 'latin').get('typeface'), 'Times New Roman')
        self.assertEqual(check_state(root, output, [[coloring]], 0), [])

    def test_compatibility_prefix_survives_without_prefixed_elements(self):
        xml = b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:v="urn:schemas-microsoft-com:vml"><mc:AlternateContent><mc:Choice Requires="v"><p:pic /></mc:Choice><mc:Fallback><p:pic /></mc:Fallback></mc:AlternateContent></p:sld>'
        output = serialize(ET.fromstring(xml), collect_ns(xml))
        self.assertEqual(collect_ns(output)['v'], 'urn:schemas-microsoft-com:vml')
        self.assertEqual(ET.fromstring(output).find('.//' + MC + 'Choice').get('Requires'), 'v')

    def test_hidden_ole_filters_legacy_preview_without_changing_shared_source(self):
        root, relations, buffer = legacy_fixture()
        rendered = clone_and_render(ET.tostring(root), [[effect('1')]], -1)
        resources = {}
        with zipfile.ZipFile(buffer) as source:
            original_data = source.read('ppt/drawings/vmlDrawing1.vml')
            self.assertTrue(check_legacy_state(source, 'ppt/slides/slide1.xml', root, source, 'ppt/slides/slide1.xml', rendered))
            copies = filter_legacy_drawings(source, 'ppt/slides/slide1.xml', root, rendered, 42, relations, resources)
            self.assertEqual(len(copies), 1)
            new_part = copies[0][1]
            remaining = [element.get('id') for element in ET.fromstring(resources[new_part]).iter(VML + 'shape')]
            self.assertEqual(remaining, ['_shape2'])
            self.assertEqual(source.read('ppt/drawings/vmlDrawing1.vml'), original_data)
            self.assertTrue(any(name.endswith('.vml.rels') for name in resources))
            output_buffer = io.BytesIO()
            with zipfile.ZipFile(output_buffer, 'w') as output:
                output.writestr('ppt/slides/_rels/slide42.xml.rels', ET.tostring(relations))
                for name, data in resources.items():
                    output.writestr(name, data)
            output_buffer.seek(0)
            with zipfile.ZipFile(output_buffer) as output:
                self.assertEqual(check_legacy_state(source, 'ppt/slides/slide1.xml', root, output, 'ppt/slides/slide42.xml', rendered), [])

    def test_no_legacy_relationship_when_all_formulas_are_hidden(self):
        root, relations, buffer = legacy_fixture()
        rendered = clone_and_render(ET.tostring(root), [[effect('1'), effect('2')]], -1)
        resources = {}
        with zipfile.ZipFile(buffer) as source:
            filter_legacy_drawings(source, 'ppt/slides/slide1.xml', root, rendered, 42, relations, resources)
        self.assertEqual(len(relations), 0)
        self.assertEqual(resources, {})

    def test_visible_formulas_keep_their_original_legacy_drawings(self):
        root, relations, buffer = legacy_fixture()
        rendered = clone_and_render(ET.tostring(root), [[effect('1'), effect('2')]], 0)
        before = signature(relations)
        resources = {}
        with zipfile.ZipFile(buffer) as source:
            filter_legacy_drawings(source, 'ppt/slides/slide1.xml', root, rendered, 46, relations, resources)
            self.assertEqual(check_legacy_state(source, 'ppt/slides/slide1.xml', root, source, 'ppt/slides/slide1.xml', rendered), [])
        self.assertEqual(signature(relations), before)
        self.assertEqual(resources, {})


class GeometryRegressionTests(unittest.TestCase):
    def fixture(self, grouped=False):
        root, tree = slide()
        shape = ET.SubElement(tree, P + ('grpSp' if grouped else 'pic'))
        nv = ET.SubElement(shape, P + ('nvGrpSpPr' if grouped else 'nvPicPr'))
        ET.SubElement(nv, P + 'cNvPr', id='1')
        props = ET.SubElement(shape, P + ('grpSpPr' if grouped else 'spPr'))
        transform = ET.SubElement(props, A + 'xfrm')
        ET.SubElement(transform, A + 'off', x='1000', y='2000')
        ET.SubElement(transform, A + 'ext', cx='4000', cy='2000')
        if grouped:
            ET.SubElement(transform, A + 'chOff', x='0', y='0')
            ET.SubElement(transform, A + 'chExt', cx='4000', cy='2000')
            shape.append(textbox('2'))
        else:
            fill = ET.SubElement(shape, P + 'blipFill')
            ET.SubElement(fill, A + 'srcRect', l='10000', r='20000')
        return root, shape

    def add_behavior(self, root, cls, tag, attributes=None, sid='1'):
        timing = root.find(P + 'timing')
        if timing is None:
            timing = ET.SubElement(root, P + 'timing')
            main = ET.SubElement(timing, P + 'cTn', nodeType='mainSeq')
            click = ET.SubElement(ET.SubElement(main, P + 'childTnLst'), P + 'par')
            effects = ET.SubElement(ET.SubElement(click, P + 'cTn'), P + 'childTnLst')
        else:
            effects = timing.find('.//' + P + 'childTnLst/' + P + 'par/' + P + 'cTn/' + P + 'childTnLst')
        effect_node = ET.SubElement(ET.SubElement(effects, P + 'par'), P + 'cTn', presetClass=cls, presetID='6', fill='hold')
        behavior = ET.SubElement(ET.SubElement(effect_node, P + 'childTnLst'), P + tag, attributes or {})
        common = ET.SubElement(behavior, P + 'cBhvr')
        ET.SubElement(common, P + 'cTn', fill='hold')
        ET.SubElement(ET.SubElement(common, P + 'tgtEl'), P + 'spTgt', spid=sid)
        return behavior

    def test_picture_moves_to_layout_endpoint_and_scales_without_changing_crop(self):
        root, picture = self.fixture()
        self.add_behavior(root, 'path', 'animMotion', {'origin': 'layout', 'path': 'M 0.01 0.02 L 0.2 -0.25 E'})
        scale = self.add_behavior(root, 'emph', 'animScale')
        ET.SubElement(scale, P + 'by', x='50000', y='50000')
        groups, notes = parse_slide_animation(root)
        self.assertEqual(notes, [])
        before = clone_and_render(ET.tostring(root), groups, -1, (10000, 6000))
        self.assertEqual(signature(shape_index(before)[('1', ())][0]), signature(picture))
        output = clone_and_render(ET.tostring(root), groups, 0, (10000, 6000))
        actual = shape_index(output)[('1', ())][0]
        transform = actual.find(P + 'spPr/' + A + 'xfrm')
        self.assertEqual(transform.find(A + 'off').attrib, {'x': '4000', 'y': '1000'})
        self.assertEqual(transform.find(A + 'ext').attrib, {'cx': '2000', 'cy': '1000'})
        self.assertEqual(signature(actual.find(P + 'blipFill')), signature(picture.find(P + 'blipFill')))
        self.assertEqual(check_state(root, output, groups, 0, (10000, 6000)), [])
        self.assertTrue(check_state(root, root, groups, 0, (10000, 6000)))

    def test_group_scale_preserves_child_geometry_and_scales_editable_labels(self):
        root, group = self.fixture(grouped=True)
        scale = self.add_behavior(root, 'emph', 'animScale')
        ET.SubElement(scale, P + 'by', x='50000', y='50000')
        groups, notes = parse_slide_animation(root)
        self.assertEqual(notes, [])
        output = clone_and_render(ET.tostring(root), groups, 0)
        actual = shape_index(output)[('1', ())][0]
        transform = actual.find(P + 'grpSpPr/' + A + 'xfrm')
        self.assertEqual(transform.find(A + 'off').attrib, {'x': '2000', 'y': '2500'})
        self.assertEqual(transform.find(A + 'ext').attrib, {'cx': '2000', 'cy': '1000'})
        self.assertEqual(transform.find(A + 'chExt').attrib, {'cx': '4000', 'cy': '2000'})
        child = actual.find(P + 'sp')
        original_child = group.find(P + 'sp')
        self.assertEqual(signature(child.find(P + 'spPr')), signature(original_child.find(P + 'spPr')))
        self.assertEqual([run.text for run in child.iter(A + 't')], [run.text for run in original_child.iter(A + 't')])
        self.assertEqual([props.get('sz') for props in child.iter(A + 'rPr')], ['1000', '1000', '1000'])
        self.assertEqual(child.find(P + 'txBody/' + A + 'bodyPr').get('lIns'), '45720')
        self.assertEqual(check_state(root, output, groups, 0), [])
        next(child.iter(A + 'rPr')).set('sz', '2000')
        self.assertTrue(check_state(root, output, groups, 0))

    def test_auto_reversed_scale_keeps_the_original_size(self):
        root, picture = self.fixture()
        scale = self.add_behavior(root, 'emph', 'animScale')
        scale.find(P + 'cBhvr/' + P + 'cTn').set('autoRev', '1')
        ET.SubElement(scale, P + 'by', x='105000', y='105000')
        groups, notes = parse_slide_animation(root)
        self.assertEqual(notes, [])
        output = clone_and_render(ET.tostring(root), groups, 0)
        self.assertEqual(signature(shape_index(output)[('1', ())][0]), signature(picture))

    def test_curved_motion_is_reported_instead_of_guessed(self):
        root, picture = self.fixture()
        self.add_behavior(root, 'path', 'animMotion', {'origin': 'layout', 'path': 'M 0 0 C 0.1 0.1 0.2 0.3 0.4 0.5 E'})
        groups, notes = parse_slide_animation(root)
        self.assertTrue(notes)
        output = clone_and_render(ET.tostring(root), groups, 0, (10000, 6000))
        self.assertEqual(signature(shape_index(output)[('1', ())][0]), signature(picture))

    def test_nested_motion_is_reported_instead_of_using_slide_coordinates(self):
        root, group = self.fixture(grouped=True)
        self.add_behavior(root, 'path', 'animMotion', {'origin': 'layout', 'path': 'M 0 0 L 0.2 0.3'}, sid='2')
        groups, notes = parse_slide_animation(root)
        self.assertTrue(notes)
        output = clone_and_render(ET.tostring(root), groups, 0, (10000, 6000))
        self.assertEqual(signature(shape_index(output)[('1', ())][0]), signature(group))

    def test_textbox_scale_is_reported_without_reflowing_text(self):
        root, tree = slide()
        text = textbox('1')
        tree.append(text)
        scale = self.add_behavior(root, 'emph', 'animScale')
        ET.SubElement(scale, P + 'by', x='50000', y='50000')
        groups, notes = parse_slide_animation(root)
        self.assertTrue(notes)
        output = clone_and_render(ET.tostring(root), groups, 0)
        self.assertEqual(signature(shape_index(output)[('1', ())][0]), signature(text))


if __name__ == '__main__':
    unittest.main()
