from unittest import TestCase

import mock

from . import base


class BaseLedgerTest(TestCase):

    def setUp(self):
        self.ledger = base.BaseLedger()
        self.ledger_kwargs = {
            'source_path': 'easy_images/fake.gif',
            'opts': {'fit': (128, 128)},
        }
        fake_filenameinfo = mock.Mock(self.ledger.filename_info_class)
        fake_filenameinfo.src_dir = 'adir/'
        fake_filenameinfo.hash = 'ahash'
        fake_filenameinfo.ext = '.ext'
        self.ledger.filename_info_class = (
            lambda *args, **kwargs: fake_filenameinfo)

    def test_meta(self):
        meta = self.ledger.meta(**self.ledger_kwargs)
        self.assertEqual(meta, {})

    def test_hash(self):
        ledger_hash = self.ledger.hash(**self.ledger_kwargs)
        self.assertEqual(ledger_hash, 'ahash')

    def test_meta_list(self):
        self.ledger.meta = mock.Mock(return_value={})
        opts = {'fit': (128, 128)}
        meta_list = self.ledger.meta_list(
            [('a/1.jpg', opts), ('b/2.jpg', opts), ('c/3.jpg', opts)])
        self.assertEqual(meta_list, [{}, {}, {}])
        self.assertEqual(self.ledger.meta.call_count, 3)

    def test_build_filename(self):
        filename = self.ledger.build_filename(**self.ledger_kwargs)
        self.assertEqual(filename, 'adir/ahash.ext')

    def test_build_filename_custom(self):
        filename = self.ledger.build_filename(
            source_path='easy_images/fake.jpg',
            opts={
                'fit': (128, 128),
                'FILENAME_FORMAT': '{info.hash}{info.ext}',
            })
        self.assertEqual(filename, 'ahash.ext')

    def test_output_extension(self):
        self.ledger.meta = mock.Mock(return_value={})
        ext = self.ledger.output_extension(
            source_ext='.png', **self.ledger_kwargs)
        self.assertEqual(ext, '.jpg')

    def test_output_extension_transparent(self):
        self.ledger.meta = mock.Mock(return_value={'transparent': True})
        ext = self.ledger.output_extension(
            source_ext='.png', **self.ledger_kwargs)
        self.assertEqual(ext, '.png')

    def test_output_extension_passed_meta(self):
        self.ledger.meta = mock.Mock(return_value={})
        self.ledger.output_extension(
            meta={}, source_ext='.png', **self.ledger_kwargs)
        self.assertFalse(self.ledger.meta.called)
