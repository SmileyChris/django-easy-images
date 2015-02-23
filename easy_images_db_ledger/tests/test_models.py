from django.test import TestCase

from easy_images_db_ledger import models


class MetaJsonTest(TestCase):

    def test_none(self):
        self.assertEqual(models.meta_json(None), None)

    def test_valid(self):
        text = '{"test": null}'
        self.assertEqual(models.meta_json(text), {'test': None})

    def test_not_dict(self):
        text = '"valid json, but not dict"'
        self.assertEqual(models.meta_json(text), {})

    def test_invalid(self):
        self.assertEqual(models.meta_json('}{'), {})


class ProcessedImageTest(TestCase):

    def test_str(self):
        obj = models.ProcessedImage(
            hash='abc', src_hash='def', opts_hash='ghi')
        self.assertEqual(str(obj), 'abc')
