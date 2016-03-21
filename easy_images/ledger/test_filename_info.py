from unittest import TestCase

import mock

from .base import BaseLedger
from .filename_info import FilenameInfo


class FilenameInfoTest(TestCase):

    def setUp(self):
        self.mock_ledger = mock.Mock(
            BaseLedger, **{
                'output_extension.return_value': '.jpg',
            })
        self.mock_ledger.highres_infix = '@{highres}x'
        self.info = FilenameInfo(
            source_path='easy_images/fake.png', opts={
                'upscale': True,
                'crop': (64, 64),
            },
            ledger=self.mock_ledger)
        self.info.make_hash = lambda text: text.upper()

    def test_make_hash(self):
        real_hash_info = FilenameInfo(
            source_path='easy_images/fake.png', opts={
                'upscale': True,
                'crop': (64, 64),
            },
            ledger=self.mock_ledger)
        self.assertEqual(
            real_hash_info.make_hash('abc'), 'qZk-NkcGgWq6PiVxeFDCbJzQ2J0')

    def test_src_dir(self):
        self.assertEqual(self.info.src_dir, 'easy_images/')

    def test_src_hash(self):
        self.assertEqual(self.info.src_hash, 'EASY_IMAGES/FAKE.PNG')

    def test_opts(self):
        self.assertEqual(self.info.opts, 'crop-64,64_upscale')

    def test_opts_hash(self):
        self.assertEqual(self.info.opts_hash, 'CROP-64,64_UPSCALE')

    def test_hash(self):
        self.assertEqual(
            self.info.hash, 'EASY_IMAGES/FAKE.PNG:CROP-64,64_UPSCALE')

    def test_src_name(self):
        self.assertEqual(self.info.src_name, 'fake')

    def test_src_ext(self):
        self.assertEqual(self.info.src_ext, '.png')

    def test_ext(self):
        self.assertEqual(self.info.ext, '.jpg')

    def test_unique_ext(self):
        # Different ext
        self.assertEqual(self.info.unique_ext, '.jpg')
        # Same ext
        same_ext_info = FilenameInfo(
            source_path='easy_images/fake.jpg', opts={},
            ledger=self.mock_ledger)
        self.assertEqual(same_ext_info.unique_ext, '')

    def test_unique_ext_highres(self):
        opts = {'HIGHRES': 4}
        info = FilenameInfo(
            source_path='easy_images/fake.png', opts=opts,
            ledger=self.mock_ledger)
        # Different ext
        self.assertEqual(info.unique_ext, '@4x.jpg')
        # Same ext
        same_ext_info = FilenameInfo(
            source_path='easy_images/fake.jpg', opts=opts,
            ledger=self.mock_ledger)
        self.assertEqual(same_ext_info.unique_ext, '@4x.jpg')

    def test_change_opts(self):
        self.info.opts = {'crop': (64, 64)}
        before = self.info.opts
        self.info.opts = {'size': (64, 64)}
        self.assertNotEqual(before, self.info.opts)
