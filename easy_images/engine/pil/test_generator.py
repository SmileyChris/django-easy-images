from unittest import TestCase

import mock

from . import generator


class PILGeneratorTest(TestCase):

    def setUp(self):
        self.generator = generator.PILGenerator()

    def test_get_processors(self):
        self.assertEqual(
            self.generator.get_processors(),
            generator.PILGenerator.default_processors)

    def test_generate_no_source(self):
        self.generator.get_source = mock.Mock()
        self.generator.build_source = mock.Mock(return_value=None)
        self.generator.generate({'source': 'test.jpg'})
        self.generator.get_source.assert_called_with('test.jpg')
        source = self.generator.get_source('test.jpg')
        self.generator.build_source.assert_called_with(source)

    def test_generate(self):
        # A bunch of mocks to set up...
        passthrough = lambda image, **opts: image
        fake_processor1 = mock.Mock(side_effect=passthrough)
        fake_processor2 = mock.Mock(side_effect=passthrough)
        self.generator.get_processors = mock.Mock(
            return_value=[fake_processor1, fake_processor2])
        self.generator.save = mock.Mock()
        self.generator.get_source = mock.Mock()
        self.generator.build_source = mock.Mock()
        # Now do it!
        opts = {'crop': (32, 32)}
        opts2 = {'fit': (128, 128)}
        output = self.generator.generate({
            'source': 'test.jpg',
            'all_opts': {
                'output1.jpg': opts,
                'output2.jpg': opts2,
            }
        })

        source_obj = self.generator.get_source('test.jpg')
        self.generator.build_source.assert_called_with(source_obj)
        source_image = self.generator.build_source(source_obj)
        self.assertEqual(
            fake_processor1.mock_calls,
            [mock.call(source_image, **opts), mock.call(source_image, **opts2)]
        )
        self.assertEqual(
            fake_processor2.mock_calls,
            [mock.call(source_image, **opts), mock.call(source_image, **opts2)]
        )
        self.assertEqual(
            self.generator.save.mock_calls,
            [
                mock.call(source_image, 'output1.jpg', opts),
                mock.call(source_image, 'output2.jpg', opts2),
            ])
        self.assertEqual(output, [source_image, source_image])

    def test_build_source(self):
        fake_source = object()
        with mock.patch('PIL.Image.open') as mock_image:
            output = self.generator.build_source(fake_source)
            mock_image.assert_called_with(fake_source)
            loaded_image = mock_image(fake_source)
            self.assertEqual(loaded_image.load.call_count, 2)
            self.assertEqual(output, loaded_image)

    def test_build_source_seek(self):
        fake_source = mock.Mock()
        with mock.patch('PIL.Image.open') as mock_image:
            output = self.generator.build_source(fake_source)
            loaded_image = mock_image(fake_source)
            self.assertEqual(output, loaded_image)
        fake_source.seek.assert_called_with(0)

    def test_build_source_error(self):
        fake_source = object()
        fake_image = mock.Mock()
        fake_image.load.side_effect = (IOError, None)
        image_patch = mock.patch('PIL.Image.open', return_value=fake_image)
        with image_patch:
            output = self.generator.build_source(fake_source)
        self.assertEqual(fake_image.load.call_count, 2)
        self.assertEqual(output, fake_image)
