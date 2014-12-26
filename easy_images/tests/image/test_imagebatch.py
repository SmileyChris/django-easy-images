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

    def test_iter(self):
        # Set up.
        opts = {'crop': (64, 64)}
        mock_image1 = mock.Mock(easy_images.image.EasyImage)
        mock_image1.source, mock_image1.opts = 'a/1.jpg', opts
        mock_image2 = mock.Mock(easy_images.image.EasyImage)
        mock_image2.source, mock_image2.opts = 'b/2.jpg', opts
        mock_ledger = mock.Mock(
            BaseLedger, **{
                'meta_list.return_value': [{}],
                'meta.return_value': None,
            })
        mock_engine = mock.Mock(
            BaseEngine, **{'processing_list.return_value': [True, False]})

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
