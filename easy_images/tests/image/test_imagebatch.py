from __future__ import unicode_literals
from unittest import TestCase

import mock
import easy_images.image
from easy_images.engine.base import BaseEngine
from easy_images.ledger.base import BaseLedger


class EasyImageBatchTest(TestCase):

    def test_init_sources(self):
        real_add = easy_images.image.EasyImageBatch.add
        mock_add = mock.Mock()
        easy_images.image.EasyImageBatch.add = mock_add
        try:
            sources = [
                ('a/1.jpg', {'crop': (64, 64)}),
                ('b/2.jpg', {'crop': (64, 64)}),
            ]
            easy_images.image.EasyImageBatch(sources=sources)
            mock_add.assert_has_calls([mock.call(*args) for args in sources])
        finally:
            easy_images.image.EasyImageBatch.add = real_add

    def test_add(self):
        batch = easy_images.image.EasyImageBatch(ledger='L', engine='E')
        opts = {'fit': (100, 100)}
        img = batch.add('easy_images/fake.jpg', opts)
        # Check the EasyImage instance is returned
        self.assertTrue(isinstance(img, easy_images.image.EasyImage))
        # Check that it was added to :attr:`new_images`.
        self.assertEqual(batch.new_images, [img])
        # Check that the source, opts were set correctly.
        self.assertEqual(img.source_path, 'easy_images/fake.jpg')
        self.assertEqual(img.opts, opts)
        self.assertEqual(img.ledger, 'L')
        # Check that the ledger and engine were set from the batch.
        self.assertEqual(img.engine, 'E')

    def create_mock_images(self, count, **kwargs):
        opts = {'crop': (64, 64)}
        images = []
        for i in range(count):
            image = mock.Mock(easy_images.image.EasyImage)
            image.source, image.opts = 'a/test.jpg', opts
            image.source_path = image.source
            for attr, value in kwargs.items():
                setattr(image, attr, value)
            images.append(image)
        return images

    def test_iter(self):
        # Set up.
        mock_image1, mock_image2 = self.create_mock_images(2)

        mock_ledger = mock.Mock(BaseLedger)
        mock_ledger.meta_list.return_value = [{}]
        mock_ledger.meta.return_value = None

        mock_engine = mock.Mock(BaseEngine)
        mock_engine.processing_list.return_value = [True, False]

        batch = easy_images.image.EasyImageBatch(
            ledger=mock_ledger, engine=mock_engine)
        batch.loaded_images = ['A', 'B']
        batch.new_images = [mock_image1, mock_image2]

        # Trigger __iter__
        self.assertEqual(list(batch), ['A', 'B', mock_image1, mock_image2])
        self.assertEqual(batch.new_images, [])
        self.assertEqual(
            batch.loaded_images, ['A', 'B', mock_image1, mock_image2])

        # Image 1 was "in processing", so only image 2 will have it's meta
        # set.
        self.assertTrue(isinstance(mock_image1.meta, mock.Mock))
        self.assertEqual(mock_image2.meta, {})

    @mock.patch.object(easy_images.image.EasyImageBatch, '__iter__')
    def test_load(self, mock_method):
        batch = easy_images.image.EasyImageBatch()
        batch.new_images = ['img1', 'img2']
        mock_method.return_value = iter([])
        self.assertEqual(batch.load(), 2)

    @mock.patch.object(easy_images.image.EasyImageBatch, '__iter__')
    def test_load_empty(self, mock_method):
        batch = easy_images.image.EasyImageBatch()
        batch.new_images = []
        mock_method.return_value = iter([])
        self.assertEqual(batch.load(), 0)
        self.assertFalse(mock_method.called)

    @mock.patch.object(easy_images.image.EasyImageBatch, '__iter__')
    def test_generate(self, mock_iter):
        images = self.create_mock_images(4, meta=None)
        images[1].meta = {}
        mock_iter.return_value = iter(images)
        mock_engine = mock.Mock(BaseEngine)
        mock_engine.processing_list.return_value = [False, False, True, False]
        mock_engine.add.return_value = []

        batch = easy_images.image.EasyImageBatch(engine=mock_engine)
        batch.new_images = images

        with mock.patch.object(easy_images.image, 'build_action') as func:
            func.return_value = []
            batch.generate()
            self.assertEqual(func.call_count, 1)
            func.assert_called_with(
                'a/test.jpg', [images[0].opts] * 2, batch.ledger)

    @mock.patch.object(easy_images.image.EasyImageBatch, '__iter__')
    def test_generate_force(self, mock_iter):
        images = self.create_mock_images(2, meta=None)
        mock_iter.return_value = iter(images)
        mock_engine = mock.Mock(BaseEngine)
        mock_engine.add.return_value = []

        batch = easy_images.image.EasyImageBatch(engine=mock_engine)
        batch.new_images = images

        with mock.patch.object(easy_images.image, 'build_action') as func:
            func.return_value = []
            batch.generate(force=True)
            self.assertFalse(mock_engine.processing_list.called)

    @mock.patch.object(easy_images.image.EasyImageBatch, '__iter__')
    def test_generate_return(self, mock_iter):
        images = self.create_mock_images(2, meta=None)
        mock_iter.return_value = iter(images)
        mock_engine = mock.Mock(BaseEngine)
        mock_engine.processing_list.return_value = [False, False]
        mock_engine.add.return_value = ['A', 'B']
        mock_engine.build_meta.side_effect = lambda img: img.lower()

        batch = easy_images.image.EasyImageBatch(engine=mock_engine)
        batch.new_images = images

        with mock.patch.object(easy_images.image, 'build_action') as func:
            func.return_value = []
            batch.generate()
            self.assertEqual(images[0].meta, 'a')
            self.assertEqual(images[1].meta, 'b')


# TODO: class AnnotateTest(TestCase):
