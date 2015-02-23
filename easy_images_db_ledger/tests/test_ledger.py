from django.test import TestCase
import mock

import easy_images_db_ledger
from easy_images_db_ledger import models


class DBLedgerTest(TestCase):

    def setUp(self):
        self.ledger = easy_images_db_ledger.DBLedger()

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

    def test_save(self):
        self.ledger.hash = mock.Mock(return_value='abcd')
        self.ledger.save('test.jpg', {'fit': (32, 32)}, {'size': (32, 32)})
        processed_image = models.ProcessedImage.objects.get()
        self.assertEqual(processed_image.pk, 'abcd')
        meta = processed_image.meta_json
        self.assertIn('date', meta)
        del meta['date']
        self.assertEqual(meta, {'size': [32, 32]})

    def test_save_overwrite(self):
        models.ProcessedImage.objects.bulk_create([
            models.ProcessedImage(pk='dblttso'),
            models.ProcessedImage(pk='dblttso2'),
        ])
        self.ledger.hash = mock.Mock(return_value='dblttso')
        self.ledger.save('test.jpg', {'fit': (32, 32)}, {'size': (32, 32)})
        self.assertEqual(models.ProcessedImage.objects.count(), 2)
        processed_image = models.ProcessedImage.objects.get(pk='dblttso')
        meta = processed_image.meta_json
        self.assertIn('date', meta)
        del meta['date']
        self.assertEqual(meta, {'size': [32, 32]})


class CachedDBLedgerTest(TestCase):

    def setUp(self):
        self.ledger = easy_images_db_ledger.CachedDBLedger()

    def test_meta(self):
        meta = {'fish': True}
        models.ProcessedImage.objects.create(pk='cdblttm')
        self.ledger.hash = mock.Mock(return_value='cdblttm')
        patch_model = mock.patch.object(
            models.ProcessedImage, 'meta_json', new_callable=mock.PropertyMock)
        with patch_model as mocked_meta_json:
            mocked_meta_json.return_value = meta
            # First call will trigger machinery.
            output = self.ledger.meta(
                source_path='test.jpg', opts={'fit': (100, 100)})
            self.assertEqual(output, meta)
            self.assertTrue(mocked_meta_json.called)
            mocked_meta_json.reset_mock()
            # Second call will just access cache.
            output = self.ledger.meta(
                source_path='test.jpg', opts={'fit': (100, 100)})
            self.assertEqual(output, meta)
            self.assertFalse(mocked_meta_json.called)

    def test_meta_list(self):
        models.ProcessedImage.objects.bulk_create([
            models.ProcessedImage(pk='cdblt1.jpg', meta='TEST1'),
            models.ProcessedImage(pk='cdblt3.jpg', meta='TEST2'),
            models.ProcessedImage(pk='cdblt4.jpg', meta='TEST3'),
        ])
        opts = {'fit': (100, 100)}
        sources = [
            ('cdblt1.jpg', opts), ('cdblt2.jpg', opts), ('cdblt3.jpg', opts)]
        self.ledger.hash = mock.Mock(side_effect=lambda *args: args[0])
        sources = [
            ('cdblt1.jpg', opts), ('cdblt2.jpg', opts), ('cdblt3.jpg', opts)]
        expected = [{'example': 'TEST1'}, None, {'example': 'TEST2'}]
        with mock.patch.object(models, 'meta_json') as mock_meta_json:
            mock_meta_json.side_effect = lambda *args: {'example': args[0]}

            output = self.ledger.meta_list(sources=sources)
            self.assertEqual(output, expected)
            self.assertEqual(mock_meta_json.call_count, 2)

            mock_meta_json.reset_mock()
            sources.append(('cdblt4.jpg', opts))
            expected.append({'example': 'TEST3'})
            output = self.ledger.meta_list(sources=sources)
            self.assertEqual(output, expected)
            self.assertEqual(mock_meta_json.call_count, 1)

            mock_meta_json.reset_mock()
            output = self.ledger.meta_list(sources=sources)
            self.assertEqual(output, expected)
            self.assertEqual(mock_meta_json.call_count, 0)

    def test_save(self):
        self.ledger.hash = mock.Mock(return_value='cdbltts')
        patch_image_cache = mock.patch(
            'easy_images_db_ledger.ledger.image_cache')
        with patch_image_cache as mock_image_cache:
            output = self.ledger.save(
                source_path='test.jpg', opts={'fit': (100, 100)},
                meta={'size': (100, 120)})
            mock_image_cache.set.assert_called_with(
                'cdbltts', {'size': (100, 120)}, timeout=None)
        self.assertEqual(self.ledger.hash.call_count, 1)
        obj = models.ProcessedImage.objects.get()
        self.assertEqual(output, obj)
