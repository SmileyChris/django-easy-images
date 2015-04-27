import json
from unittest import TestCase

from django import template
import mock

from easy_images.templatetags import easy_images as tags


class ImageFilterTest(TestCase):

    def test_basic(self):
        t = template.Template(
            '{% load easy_images %}{{ "test.jpg"|image:opts }}')
        with mock.patch.object(tags, 'EasyImage') as mocked:
            mocked.return_value = 'fish'
            output = t.render(template.Context({'opts': {'size': (10, 10)}}))
            self.assertEqual(output, 'fish')

    def test_alias(self):
        t = template.Template(
            '{% load easy_images %}{{ "test.jpg"|image:"alias" }}')
        with mock.patch.object(tags.aliases, 'get') as aliases_mock:
            aliases_mock.return_value = {'size': (10, 10)}
            with mock.patch.object(tags, 'EasyImage') as easy_image_mock:
                easy_image_mock.return_value = 'fish'
                output = t.render(template.Context())
                self.assertEqual(output, 'fish')
            aliases_mock.assert_called_with('alias')

    def test_bad_alias(self):
        t = template.Template(
            '{% load easy_images %}{{ "test.jpg"|image:"alias" }}')
        with mock.patch.object(tags.aliases, 'get') as aliases_mock:
            aliases_mock.return_value = None
            with mock.patch.object(tags, 'EasyImage') as easy_image_mock:
                easy_image_mock.return_value = 'fish'
                output = t.render(template.Context())
                self.assertEqual(output, '')
                self.assertFalse(easy_image_mock.called)
            aliases_mock.assert_called_with('alias')


class ImageAliasTagTest(TestCase):

    def test_basic(self):
        t = template.Template(
            '{% load easy_images %}{% image_alias "alias" as a %}{{ a.size }}')
        with mock.patch.object(tags.aliases, 'get') as aliases_mock:
            aliases_mock.return_value = {'size': (10, 10)}
            output = t.render(template.Context())
            self.assertEqual(output, '(10, 10)')
            aliases_mock.assert_called_with('alias', app_name=None)

    def test_bad_alias(self):
        t = template.Template(
            '{% load easy_images %}{% image_alias "alias" as a %}{{ a.size }}')
        with mock.patch.object(tags.aliases, 'get') as aliases_mock:
            aliases_mock.return_value = None
            output = t.render(template.Context())
            self.assertEqual(output, '')
            aliases_mock.assert_called_with('alias', app_name=None)


class ImageTag(TestCase):

    def setUp(self):
        self.patcher = mock.patch.object(tags, 'EasyImage')
        self.EasyImage = self.patcher.start()
        self.EasyImage.side_effect = (
            lambda source, opts: json.dumps(opts, sort_keys=True))

    def tearDown(self):
        self.patcher.stop()

    def test_basic(self):
        t = template.Template(
            '{% load easy_images %}{% image "test.jpg" value=1 a %}')
        output = t.render(template.Context())
        self.assertEqual(output, '{"a": true, "value": 1}')

    def test_as(self):
        t = template.Template(
            '{% load easy_images %}'
            '{% image "test.jpg" value=1 a as a %}---{{ a|safe }}')
        output = t.render(template.Context())
        self.assertEqual(output, '---{"a": true, "value": 1}')

    def test_strip_none(self):
        t = template.Template(
            '{% load easy_images %}{% image "test.jpg" value1=a value2=b %}')
        output = t.render(template.Context({'a': 'A'}))
        self.assertEqual(output, '{"value1": "A"}')

    def test_dimensions(self):
        t = template.Template(
            '{% load easy_images %}{% image "test.jpg" crop=100x200 %}')
        output = t.render(template.Context())
        self.assertEqual(output, '{"crop": [100, 200]}')

    def test_invalid(self):
        self.assertRaises(
            template.TemplateSyntaxError, template.Template,
            '{% load easy_images %}{% image "test.jpg" %}')


class PopulateFromContext(TestCase):

    def test_noop(self):
        mock_context = mock.MagicMock()
        batch = mock_context.render_context.get()

        # batch.__bool__.return_value = False
        batch.__nonzero__.return_value = False
        tags._populate_from_context(image=object(), context=mock_context)
        self.assertFalse(batch.add_image.called)
        self.assertFalse(batch.set_meta.called)

    def test_no_context(self):
        output = tags._populate_from_context(image=object(), context=None)
        self.assertEqual(output, None)

    def test_set_meta(self):
        mock_context = mock.MagicMock()
        batch = mock_context.render_context.get()
        batch.gathering = None
        image = object()

        tags._populate_from_context(image=image, context=mock_context)
        self.assertFalse(batch.add_image.called)
        batch.set_meta.assert_called_with(image)

    def test_gathering(self):
        mock_context = mock.MagicMock()
        batch = mock_context.render_context.get()
        batch.gathering = True
        image = object()

        tags._populate_from_context(image=image, context=mock_context)
        self.assertFalse(batch.set_meta.called)
        batch.add_image.assert_called_with(image)


class ImageOptsFilter(TestCase):

    def setUp(self):
        self.image = mock.NonCallableMock(
            spec=tags.EasyImage, source='test.jpg', opts={'fish': 'food'})
        self.mock_patcher = mock.patch.object(tags, 'EasyImage')
        self.EasyImage = self.mock_patcher.start()
        self.EasyImage.return_value = 'out'

    def tearDown(self):
        self.mock_patcher.stop()

    def test_number(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"TEST=1.5" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(
            source='test.jpg', opts={'fish': 'food', 'TEST': 1.5})

    def test_text(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"TEST=abc" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(
            source='test.jpg', opts={'fish': 'food', 'TEST': 'abc'})

    def test_bool(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"TEST" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(
            source='test.jpg', opts={'fish': 'food', 'TEST': True})

    def test_none(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"TEST=None" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(
            source='test.jpg', opts={'fish': 'food'})

    def test_override(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"fish=friends shark" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(
            source='test.jpg', opts={'fish': 'friends', 'shark': True})

    def test_override_remove(self):
        t = template.Template(
            '{% load easy_images %}{{ image|imageopts:"fish=None" }}')
        output = t.render(template.Context({'image': self.image}))
        self.assertEqual(output, 'out')
        self.EasyImage.assert_called_with(source='test.jpg', opts={})


class GetFilterContext(TestCase):

    def fake_template_render(self):
        return tags.get_filter_context()

    def test_stack(self):
        context = object()
        self.assertEqual(self.fake_template_render(), context)

    def test_missing_returns_empty_dict(self):
        self.assertEqual(self.fake_template_render(), {})


class ImageBatch(TestCase):

    def test_no_content_rendered(self):
        t = template.Template(
            '{% load easy_images %}{% imagebatch %}test{% endimagebatch %}')
        output = t.render(template.Context())
        self.assertEqual(output, '')
