from __future__ import unicode_literals
from unittest import TestCase

import mock
import easy_images.image
from easy_images.engine.base import BaseEngine
from easy_images.ledger.base import BaseLedger


class EasyImageTest(TestCase):

    def build_image(self, **kwargs):
        if 'source' not in kwargs:
            kwargs['source'] = 'easy_images/fake.jpg'
        if 'opts' not in kwargs:
            kwargs['opts'] = {'upscale': True, 'crop': (64, 64)}
        if 'ledger' not in kwargs:
            kwargs['ledger'] = mock.Mock(
                BaseLedger, **{'meta.return_value': None})
        if 'engine' not in kwargs:
            kwargs['engine'] = mock.Mock(
                BaseEngine, **{'add.return_value': []})
        processing = kwargs.pop('is_processing', False)
        kwargs['engine'].configure_mock(
            **{'processing.return_value': processing})
        return easy_images.image.EasyImage(**kwargs)

    def test_name(self):
        ledger = mock.Mock(
            BaseLedger, **{'build_filename.return_value': 'output.jpg'})
        img = self.build_image(ledger=ledger)
        self.assertEqual(img.name, 'output.jpg')

    def test_hash(self):
        filename_info = mock.Mock()
        filename_info.hash = 'hashhashhash'
        ledger = mock.Mock(
            BaseLedger, **{'get_filename_info.return_value': filename_info})
        img = self.build_image(ledger=ledger)
        self.assertEqual(img.hash, 'hashhashhash')

    def test_processing(self):
        img = self.build_image(is_processing=True)
        self.assertTrue(img.processing)
        self.assertTrue(img.engine.processing.called)

        img_not_processing = self.build_image()
        self.assertFalse(img_not_processing.processing)
        self.assertTrue(img_not_processing.engine.processing.called)

    def test_exists(self):
        img = self.build_image()
        self.assertFalse(img.exists)
        self.assertTrue(img.ledger.meta.called)
        self.assertEqual(img.engine.processing.call_count, 1)
        img.meta = {}
        self.assertTrue(img.exists)
        self.assertEqual(img.engine.processing.call_count, 2)

    def test_exists_processing(self):
        img = self.build_image(is_processing=True)
        self.assertFalse(img.exists)
        self.assertFalse(img.ledger.meta.called)
        self.assertEqual(img.engine.processing.call_count, 1)
        img.meta = {}
        self.assertFalse(img.exists)
        self.assertEqual(img.engine.processing.call_count, 2)

    def test_exists_dont_check_processing(self):
        img = self.build_image(always_check_processing=False)
        self.assertFalse(img.exists)
        self.assertEqual(img.engine.processing.call_count, 1)
        img.meta = {}
        self.assertTrue(img.exists)
        self.assertEqual(img.engine.processing.call_count, 1)

    def test_build_url(self):
        expected = 'https://example.com/output.jpg'
        mock_storage = mock.Mock(**{'url.return_value': expected})
        engine = mock.Mock(
            BaseEngine, **{'get_generated_storage.return_value': mock_storage})
        img = self.build_image(engine=engine)
        self.assertEqual(img.build_url(), expected)

    def test_url_if_generated(self):
        expected = 'https://example.com/uig.jpg'
        img = self.build_image()
        img.generate = mock.Mock(return_value=True)
        img.build_url = mock.Mock(return_value=expected)
        self.assertEqual(img.url, expected)
        self.assertTrue(img.generate.called)

    def test_url_if_not_generated(self):
        expected = 'https://example.com/uing.jpg'
        engine = mock.Mock(
            BaseEngine, **{'processing_url.return_value': expected})
        img = self.build_image(engine=engine)
        img.generate = mock.Mock(return_value=None)
        self.assertEqual(img.url, expected)
        self.assertTrue(img.generate.called)

    def test_str(self):
        expected = 'https://example.com/uig.jpg'
        img = self.build_image()
        img.generate = mock.Mock(return_value=True)
        img.build_url = mock.Mock(return_value=expected)
        self.assertEqual('%s' % img, expected)
        self.assertTrue(img.generate.called)

    def test_meta(self):
        img = self.build_image()
        self.assertEqual(img.meta, None)
        self.assertTrue(img.ledger.meta.called)

    def test_meta_set(self):
        img = self.build_image()
        img.meta = 'already-set'
        self.assertEqual(img.meta, 'already-set')
        self.assertFalse(img.ledger.meta.called)

    def test_width_and_height(self):
        img = self.build_image()
        # If doesn't exist
        self.assertEqual(img.width, None)
        self.assertEqual(img.height, None)
        # If exists but no size metadata
        img.meta = {}
        self.assertEqual(img.width, None)
        self.assertEqual(img.height, None)
        # If size metadata
        img.meta = {'size': (100, 200)}
        self.assertEqual(img.width, 100)
        self.assertEqual(img.height, 200)

    def test_get_file(self):
        img = self.build_image()
        # Doesn't exist.
        self.assertEqual(img.get_file(), None)

    def test_get_file_exists(self):
        expected = 'somefile'
        engine = mock.Mock(
            BaseEngine, **{'get_generated_file.return_value': expected})
        img = self.build_image(engine=engine)
        img.meta = {}
        self.assertEqual(img.get_file(), expected)

    def test_source_path_from_text(self):
        img = self.build_image(source='text')
        self.assertEqual(img.source_path, 'text')

    def test_source_path_from_file(self):
        # From Django file-like object
        file_obj = mock.Mock()
        file_obj.name = 'somename'
        img = self.build_image(source=file_obj)
        self.assertEqual(img.source_path, 'somename')

    def test_generate(self):
        img = self.build_image()
        img.generate()
        self.assertTrue(img.engine.add.called)
        action = img.engine.add.call_args[0][0]
        self.assertIn('KEY', action['opts'][0])

    def test_generate_exists(self):
        img = self.build_image()
        img.meta = {}   # Setting meta to non-None means the image exists.
        self.assertEqual(img.generate(), True)
        self.assertFalse(img.engine.add.called)

    def test_generate_force(self):
        img = self.build_image()
        img.generate(force=True)
        self.assertTrue(img.engine.add.called)

    def test_generate_force_exists(self):
        img = self.build_image()
        img.meta = {}   # Setting meta to non-None means the image exists.
        img.generate(force=True)
        self.assertTrue(img.engine.add.called)

    def test_generate_existing_key(self):
        img = self.build_image(opts={'fit': (128, 128), 'KEY': 'abcde'})
        img.generate()
        self.assertTrue(img.engine.add.called)
        action = img.engine.add.call_args[0][0]
        self.assertEqual(action['opts'][0].get('KEY'), 'abcde')

    def test_generate_returns_image(self):
        processed_image = object()
        engine = mock.Mock(BaseEngine)
        engine.add.return_value = [processed_image]
        img = self.build_image(engine=engine)
        self.assertEqual(img.generate(), processed_image)

    def test_loaded(self):
        image = self.build_image()
        self.assertEqual(image.loaded, False)
        image.meta
        self.assertEqual(image.loaded, True)
