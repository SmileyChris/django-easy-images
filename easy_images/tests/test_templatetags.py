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
