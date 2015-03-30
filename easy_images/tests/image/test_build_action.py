from unittest import TestCase

import mock
from easy_images.image import build_action
from easy_images.ledger.base import BaseLedger


class BuildActionTest(TestCase):

    def test_filename_transparent(self):
        ledger = BaseLedger()
        action = build_action('test.jpg', [{}], ledger)
        opts = action['opts'][0]
        self.assertEqual(opts['FILENAME'], 'RWAsltFW9jW5tvsbyqI36wTsw2s.jpg')
        self.assertEqual(
            opts['FILENAME_TRANSPARENT'], 'RWAsltFW9jW5tvsbyqI36wTsw2s.png')

    def test_no_filename_transparent(self):
        ledger = mock.Mock(BaseLedger)
        ledger.output_extension.return_value = '.jpg'
        ledger.build_filename.return_value = 'thumb.jpg'
        action = build_action('test.jpg', [{}], ledger)
        opts = action['opts'][0]
        self.assertEqual(opts.get('FILENAME'), 'thumb.jpg')
        self.assertNotIn('FILENAME_TRANSPARENT', opts)
