from unittest import TestCase

import django.core.files.storage
import easy_images.engine.default
from easy_images.engine.engine_image import BaseEngineImage
import mock

from . import base


class TestEngine(base.BaseEngine):

    def build_source(self, *args, **kwargs):
        raise NotImplementedError   # pragma: nocover

    def process_image(self, *args, **kwargs):
        raise NotImplementedError   # pragma: nocover


class TransparentEngineImage(BaseEngineImage):
    transparent = True


class BaseTestCase(TestCase):

    def setUp(self):
        self.engine = TestEngine()
        self.example_action = {
            'source': 'fake.jpg',
            'opts': [
                {
                    'KEY': 'fit_key',
                    'FILENAME': 'fit.jpg',
                    'fit': (200, 0),
                },
                {
                    'KEY': 'crop_key',
                    'FILENAME': 'crop.jpg',
                    'FILENAME_TRANSPARENT': 'crop.png',
                    'crop': (64, 64),
                    'upscale': True,
                },
            ],
        }


class BaseEngineTest(BaseTestCase):

    def test_abc_protection(self):
        self.assertRaises(TypeError, base.BaseEngine)

    def test_add(self):
        self.engine.generate = mock.Mock(return_value=None)
        self.engine.add(self.example_action)
        self.engine.generate.assert_called_once_with(self.example_action)

    @mock.patch.object(base.default_ledger, 'save')
    def test_generate_and_record(self, ledger_save):
        self.engine.generate = mock.Mock(return_value=None)
        self.engine.generate_and_record(action=self.example_action)
        self.assertEqual(self.engine.generate.call_count, 1)
        self.assertEqual(ledger_save.call_count, 2)

    def test_generate_and_record_custom_ledger(self):
        self.engine.generate = mock.Mock(return_value=None)
        ledger = 'easy_images.ledger.base.BaseLedger'
        self.example_action['ledger'] = ledger
        with mock.patch(ledger + '.save') as ledger_save:
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
        file_obj = mock.Mock()
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
        engine_image = mock.Mock(BaseEngineImage)
        engine_image.opts = {}
        self.engine.save('test.jpg', engine_image)
        self.assertTrue(engine_image.bytes.called)
        self.assertTrue(fake_storage.save.called)

    def test_build_meta(self):
        image = BaseEngineImage(image=mock.Mock(size=(100, 200)), opts={})
        self.assertEqual(self.engine.build_meta(image), {'size': (100, 200)})

        transparent_image = TransparentEngineImage(
            image=mock.Mock(size=(300, 400)), opts={})
        self.assertEqual(
            self.engine.build_meta(transparent_image),
            {'size': (300, 400), 'transparent': True})

    def test_build_meta_empty(self):
        self.assertEqual(self.engine.build_meta(None), {})


class BaseEngineGenerateTest(BaseTestCase):

    def setUp(self):
        super(BaseEngineGenerateTest, self).setUp()
        self.engine.get_source_file = mock.Mock()
        self.engine.build_source = mock.Mock()
        self.engine.process_image = mock.Mock(return_value=None)
        self.engine.save = mock.Mock()

    # def call_generate(self, engine_image_class=BaseEngineImage):
    #     self.engine.get_source_file = mock.Mock()
    #     self.engine.build_source = mock.Mock()
    #     self.engine.process_image = mock.Mock(
    #         return_value=engine_image_class(object(), {}))
    #     self.engine.save = mock.Mock()

    #     self.engine.generate(self.example_action)
    #     return [calls[0][0] for calls in self.engine.save.call_args_list]

    # def test_generate(self):
    #     self.call_generate()
    #     self.assertEqual(self.engine.get_source_file.call_count, 1)
    #     self.assertEqual(self.engine.build_source.call_count, 1)
    #     self.assertEqual(self.engine.process_image.call_count, 2)
    #     self.assertEqual(self.engine.save.call_count, 2)

    # def test_generate_no_opts(self):
    #     del self.example_action['opts']
    #     self.assertEqual(self.engine.generate(self.example_action), [])

    # def test_generate_no_source_image(self):
    #     self.engine.get_source_file = mock.Mock()
    #     self.engine.build_source = mock.Mock(return_value=None)
    #     self.assertEqual(self.engine.generate(self.example_action), [])

    # def test_generate_saves_filename(self):
    #     save_filenames = self.call_generate()
    #     self.assertEqual(save_filenames, ['fit.jpg', 'crop.jpg'])

    # def test_generate_saves_transparent_filename(self):
    #     save_filenames = self.call_generate(
    #         engine_image_class=TransparentEngineImage)
    #     self.assertEqual(save_filenames, ['fit.jpg', 'crop.png'])

    def test_no_opts(self):
        output = self.engine.generate(action={})
        self.assertEqual(output, [])
        output = self.engine.generate(action={'opts': []})
        self.assertEqual(output, [])
        self.assertFalse(self.engine.get_source_file.called)

    def test_no_source_image(self):
        self.engine.build_source.return_value = None
        output = self.engine.generate(self.example_action)
        self.assertEqual(output, [])
        self.assertTrue(self.engine.get_source_file.called)
        self.engine.build_source.assert_called_with(
            self.engine.get_source_file())
        self.assertFalse(self.engine.process_image.called)

    def test_save_output(self):
        img1 = mock.MagicMock(transparent=False)
        self.engine.process_image.side_effect = [img1, None]
        output = self.engine.generate(self.example_action)
        self.assertEqual(output, [img1, None])

    def test_save(self):
        self.engine.process_image = mock.Mock(
            return_value=BaseEngineImage('source.jpg', {}))
        self.engine.generate(self.example_action)
        self.assertEqual(self.engine.save.call_count, 2)
        save_filenames = [
            calls[0][0] for calls in self.engine.save.call_args_list]
        self.assertEqual(save_filenames, ['fit.jpg', 'crop.jpg'])

    def test_save_transparent(self):
        self.engine.process_image = mock.Mock(
            return_value=TransparentEngineImage('source.jpg', {}))
        self.engine.generate(self.example_action)
        self.assertEqual(self.engine.save.call_count, 2)
        save_filenames = [
            calls[0][0] for calls in self.engine.save.call_args_list]
        self.assertEqual(save_filenames, ['fit.jpg', 'crop.png'])
