from django.test import TestCase
import mock

from easy_images_db_ledger import ledger, models


class LedgerTest(TestCase):

    def setUp(self):
        self.ledger = ledger.DBLedger()

    def test_meta(self):
        meta = {'fish': True}
        models.ProcessedImage.objects.create(pk='abcd')
        self.ledger.hash = mock.Mock(return_value='abcd')
        patch_model = mock.patch.object(
            models.ProcessedImage, 'meta_json', new_callable=mock.PropertyMock)
        with patch_model as mocked_model:
            mocked_model.return_value = meta
            output = self.ledger.meta(
                source_path='test.jpg', opts={'fit': (100, 100)})
        self.assertEqual(output, meta)

    def test_meta_explicit_hash(self):
        meta = {'fish': True}
        models.ProcessedImage.objects.create(pk='abcd')
        self.ledger.hash = mock.Mock()
        patch_model = mock.patch.object(
            models.ProcessedImage, 'meta_json', new_callable=mock.PropertyMock)
        with patch_model as mocked_model:
            mocked_model.return_value = meta
            output = self.ledger.meta(
                source_path='test.jpg', opts={'fit': (100, 100)},
                image_hash='abcd')
        self.assertFalse(self.ledger.hash.called)
        self.assertEqual(output, meta)

    def test_meta_missing(self):
        models.ProcessedImage.objects.create(pk='efgh')
        self.ledger.hash = mock.Mock(return_value='abcd')
        output = self.ledger.meta(
            source_path='test.jpg', opts={'fit': (100, 100)})
        self.assertEqual(output, None)

    def test_meta_explicit_hash_missing(self):
        self.ledger.hash = mock.Mock()
        output = self.ledger.meta(
            source_path='test.jpg', opts={'fit': (100, 100)},
            image_hash='abcd')
        self.assertFalse(self.ledger.hash.called)
        self.assertEqual(output, None)

    def test_meta_list(self):
        models.ProcessedImage.objects.bulk_create([
            models.ProcessedImage(pk='test1.jpg', meta='TEST1'),
            models.ProcessedImage(pk='test3.jpg', meta='TEST2'),
        ])
        opts = {'fit': (100, 100)}
        sources = [
            ('test1.jpg', opts), ('test2.jpg', opts), ('test3.jpg', opts)]
        self.ledger.hash = mock.Mock(side_effect=lambda *args: args[0])
        with mock.patch.object(
                models, 'meta_json',
                side_effect=lambda *args: {'example': args[0]}):
            output = self.ledger.meta_list(sources=sources)
        self.assertEqual(
            output, [{'example': 'TEST1'}, None, {'example': 'TEST2'}])

    def test_meta_list_explicit_hashes(self):
        models.ProcessedImage.objects.bulk_create([
            models.ProcessedImage(pk='abcd', meta='TEST1'),
            models.ProcessedImage(pk='efgh', meta='TEST2'),
        ])
        opts = {'fit': (100, 100)}
        sources = [
            ('test1.jpg', opts), ('test2.jpg', opts), ('test3.jpg', opts)]
        self.ledger.hash = mock.Mock()
        with mock.patch.object(
                models, 'meta_json',
                side_effect=lambda *args: {'example': args[0]}):
            output = self.ledger.meta_list(
                sources=sources, hashes=['abcd', 'efgh', 'ijkl'])
        self.assertFalse(self.ledger.hash.called)
        self.assertEqual(
            output, [{'example': 'TEST1'}, {'example': 'TEST2'}, None])
