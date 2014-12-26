from unittest import TestCase

import mock

from .base import BaseEngine


class BaseEngineTest(TestCase):

    def setUp(self):
        self.engine = BaseEngine()
        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'all_opts': {
                'easy_images/fit.jpg': {'fit': (200, 0)},
                'easy_images/crop.jpg': {'crop': (64, 64), 'upscale': True},
            },
        }

    def test_add(self):
        self.engine.generate = mock.Mock()
        self.engine.add(self.example_action)
        self.engine.generate.assert_called_once_with(self.example_action)

    def test_generate(self):
        self.assertRaises(
            NotImplementedError, self.engine.generate, self.example_action)

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

    def test_get_source(self):
        file_obj = mock.Mock(file)
        self.assertEqual(self.engine.get_source(file_obj, opts={}), file_obj)
        expected = 'fakefile'
        mock_storage = mock.Mock(**{'open.return_value': expected})
        self.engine.get_source_storage = mock.Mock(return_value=mock_storage)
        self.assertEqual(
            self.engine.get_source('some_path', opts={}), expected)
