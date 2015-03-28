from unittest import TestCase

import django.core.files.storage
import easy_images.engine.default
import mock

from . import base


class TestEngine(base.BaseEngine):

    # def generate(self, *args, **kwargs):
    #     return 'ok, generated'

    def build_meta(self, *args, **kwargs):
        return {}

    def build_source(self, *args, **kwargs):
        raise NotImplementedError

    def is_transparent(self, *args, **kwargs):
        raise NotImplementedError

    def process_image(self, *args, **kwargs):
        raise NotImplementedError


class BaseEngineTest(TestCase):

    def setUp(self):
        self.engine = TestEngine()
        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'opts': [
                {
                    'KEY': 'fit_key',
                    'FILENAME': 'easy_images/fit.jpg',
                    'FILENAME_TRANSPARENT': 'easy_images/fit.png',
                    'fit': (200, 0),
                },
                {
                    'KEY': 'crop_key',
                    'FILENAME': 'easy_images/crop.jpg',
                    'FILENAME_TRANSPARENT': 'easy_images/crop.png',
                    'crop': (64, 64),
                    'upscale': True,
                },
            ],
        }

    def test_abc_protection(self):
        self.assertRaises(TypeError, base.BaseEngine)

    def test_add(self):
        self.engine.generate = mock.Mock(return_value=None)
        self.engine.add(self.example_action)
        self.engine.generate.assert_called_once_with(self.example_action)

    def test_generate_and_record(self):
        self.engine.generate = mock.Mock(return_value=None)
        with mock.patch.object(base.default_ledger, 'save') as ledger_save:
            self.engine.generate_and_record(action=self.example_action)
            self.assertEqual(self.engine.generate.call_count, 1)
            self.assertEqual(ledger_save.call_count, 2)

    def test_processing(self):
        self.assertFalse(self.engine.processing('hashhashhash'))

    def test_processing_list(self):
        self.engine.processing = mock.Mock(return_value=False)
        self.assertEqual(
            self.engine.processing_list(['a', 'b', 'c']),
            [False, False, False])
        self.assertEqual(self.engine.processing.call_count, 3)

    def test_processing_url(self):
        self.assertRaises(
            NotImplementedError, self.engine.processing_url,
            source_path='test.jpg', opts={'fit': (100, 100)},
            source_url='source.jpg')

    def test_get_source_file(self):
        file_obj = mock.Mock(file)
        self.assertEqual(self.engine.get_source_file(
            file_obj, opts={}), file_obj)
        expected = 'fakefile'
        mock_storage = mock.Mock(**{'open.return_value': expected})
        self.engine.get_source_storage = mock.Mock(return_value=mock_storage)
        self.assertEqual(
            self.engine.get_source_file('some_path', opts={}), expected)

    def test_get_generated_file(self):
        fake_storage = mock.Mock()
        self.engine.get_generated_storage = mock.Mock(
            return_value=fake_storage)
        self.engine.get_generated_file(
            source_path='test.jpg', opts={'fit': (100, 100)})
        self.assertTrue(fake_storage.open.called)

    def test_get_source_storage(self):
        self.assertEqual(
            self.engine.get_source_storage(opts={'fit': (100, 100)}),
            django.core.files.storage.default_storage)

    def test_get_generated_storage(self):
        self.assertEqual(
            self.engine.get_generated_storage(opts={'fit': (100, 100)}),
            easy_images.engine.default.default_storage)

    def test_save(self):
        fake_storage = mock.Mock()
        self.engine.get_generated_storage = mock.Mock(
            return_value=fake_storage)
        self.engine.save('test.jpg', object(), {})
        self.assertTrue(fake_storage.save.called)
