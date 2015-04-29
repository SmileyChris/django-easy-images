from django.test import TestCase
import django.core.files.storage

from . import default


class FakeStorage(object):
    pass


class DefaultTest(TestCase):

    def test_default_storage(self):
        with self.settings(EASY_IMAGES={'STORAGE': None}):
            storage = default.get_default_storage()
        self.assertEqual(storage, django.core.files.storage.default_storage)

    def test_custom_storage(self):
        with self.settings(EASY_IMAGES={
                'STORAGE': 'easy_images.engine.test_default.FakeStorage'}):
            storage = default.get_default_storage()
        self.assertTrue(isinstance(storage, FakeStorage))
