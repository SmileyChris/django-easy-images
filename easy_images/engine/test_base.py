from unittest import TestCase

import django.core.files.storage
import easy_images.engine.default
import mock

from . import base


class TestEngine(base.BaseEngine):

    def generate(self, *args, **kwargs):
        return 'ok, generated'


class BaseEngineTest(TestCase):

    def setUp(self):
        self.engine = TestEngine()
        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'all_opts': {
                'easy_images/fit.jpg': {'fit': (200, 0)},
                'easy_images/crop.jpg': {'crop': (64, 64), 'upscale': True},
            },
        }

    def test_abc_protection(self):
        self.assertRaises(TypeError, base.BaseEngine)

    def test_add(self):
        self.engine.generate = mock.Mock()
        self.engine.add(self.example_action)
        self.engine.generate.assert_called_once_with(self.example_action)

    def test_generate_and_record(self):
        self.engine.generate = mock.Mock()
        self.engine.record = mock.Mock()
        self.engine.generate_and_record(action=self.example_action)
        self.assertEqual(self.engine.generate.call_count, 1)
        self.assertEqual(self.engine.record.call_count, 2)

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

    def test_get_generated(self):
        fake_storage = mock.Mock()
        self.engine.get_generated_storage = mock.Mock(
            return_value=fake_storage)
        self.engine.get_generated(
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
        self.engine.save('test.jpg', object())
        self.assertTrue(fake_storage.save.called)


class BaseEngineRecordTest(TestCase):

    def setUp(self):
        self.engine = TestEngine()
        self.real_default_ledger = base.default_ledger
        base.default_ledger = mock.Mock()

    def tearDown(self):
        base.default_ledger = self.real_default_ledger

    def test_record_no_key(self):
        self.engine.record('source.jpg', {'fit': (200, 0)})
        self.assertFalse(base.default_ledger.save.called)

    def test_record(self):
        self.engine.record('source.jpg', {'fit': (200, 0), 'KEY': 'abc'})
        self.assertTrue(base.default_ledger.save.called)

    def test_record_alt_ledger(self):
        alt_ledger = mock.Mock()
        self.engine.record(
            'source.jpg', {'fit': (200, 0), 'KEY': 'abc'}, ledger=alt_ledger)
        self.assertFalse(base.default_ledger.save.called)
        self.assertTrue(alt_ledger.save.called)
