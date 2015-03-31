from unittest import TestCase

import mock

from . import engine, utils


class OutputTest(TestCase):

    def test_write_image_jpg(self):
        image = mock.Mock()
        image.size = (128, 128)
        destination = engine.EngineImage(image, {}).bytes('test.jpg')
        self.assertTrue(isinstance(destination, utils.BytesIO))
        self.assertEqual(image.save.call_count, 1)
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, progressive=True,
            quality=85)

    def test_write_image_small_jpg(self):
        image = mock.Mock()
        image.size = (32, 32)
        destination = engine.EngineImage(image, {}).bytes('test.jpg')
        self.assertTrue(isinstance(destination, utils.BytesIO))
        self.assertEqual(image.save.call_count, 1)
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, quality=85)

    def test_write_image_large_jpg(self):
        image = mock.Mock()
        image.size = (10000, 10000)
        # Fake the initial saving failing due to MAXBLOCK size.
        image.save.side_effect = [IOError, None]

        destination = engine.EngineImage(image, {}).bytes('test.jpg')
        self.assertTrue(isinstance(destination, utils.BytesIO))
        self.assertEqual(image.save.call_count, 2)
        self.assertEqual(
            image.save.mock_calls,
            [
                mock.call(
                    destination, format='JPEG', optimize=1, quality=85,
                    progressive=True),
                mock.call(
                    destination, format='JPEG', quality=85, progressive=True),
            ])

    def test_write_image_png(self):
        image = mock.Mock()
        destination = engine.EngineImage(image, {}).bytes('test.png')
        self.assertTrue(isinstance(destination, utils.BytesIO))
        self.assertEqual(image.save.call_count, 1)
        image.save.assert_called_once_with(destination, format='PNG')


class TestProgressive(TestCase):

    def test_custom_progressive_on(self):
        image = mock.Mock()
        image.size = (12, 12)

        destination = engine.EngineImage(
            image, opts=dict(progressive=True)).bytes('test.jpg')
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, progressive=True,
            quality=85)

    def test_custom_progressive_off(self):
        image = mock.Mock()
        image.size = (1200, 1200)

        destination = engine.EngineImage(
            image, opts=dict(progressive=False)).bytes('test.jpg')
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, quality=85)

    def test_custom_progressive_int(self):
        image = mock.Mock()
        image.size = (12, 12)

        destination = engine.EngineImage(
            image, opts=dict(progressive=10)).bytes('test.jpg')
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, progressive=True,
            quality=85)

        destination = engine.EngineImage(
            image, opts=dict(progressive=15)).bytes('test.jpg')
        image.save.assert_called_with(
            destination, format='JPEG', optimize=1, quality=85)
