import json
from unittest import TestCase

from django import template
import mock

from easy_images.templatetags import easy_images as tags


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


# class BatchProcessing(TestCase):

#     def test_noop(self):
#         mock_context = mock.MagicMock()
#         batch = mock_context.render_context.get()

#         # batch.__bool__.return_value = False
#         batch.__nonzero__.return_value = False
#         tags._populate_from_context(image=object(), context=mock_context)
#         self.assertFalse(batch.add_image.called)
#         self.assertFalse(batch.set_meta.called)

#     def test_no_context(self):
#         output = tags._populate_from_context(image=object(), context=None)
#         self.assertEqual(output, None)

#     def test_set_meta(self):
#         mock_context = mock.MagicMock()
#         batch = mock_context.render_context.get()
#         batch.gathering = None
#         image = object()

#         tags._populate_from_context(image=image, context=mock_context)
#         self.assertFalse(batch.add_image.called)
#         batch.set_meta.assert_called_with(image)

#     def test_gathering(self):
#         mock_context = mock.MagicMock()
#         batch = mock_context.render_context.get()
#         batch.gathering = True
#         image = object()

#         tags._populate_from_context(image=image, context=mock_context)
#         self.assertFalse(batch.set_meta.called)
#         batch.add_image.assert_called_with(image)


class ImageBatch(TestCase):

    def test_content_rendered(self):
        t = template.Template(
            '{% load easy_images %}a {% imagebatch %}test')
        output = t.render(template.Context())
        self.assertEqual(output, 'a test')
