from django.test import TestCase
import mock

from . import queue, models


class BaseEngineTest(TestCase):

    def setUp(self):
        self.queue = queue.DBQueue()
        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'all_opts': {
                'easy_images/fit.jpg': {'fit': (200, 0), 'KEY': 'abc'},
                'easy_images/crop.jpg': {
                    'crop': (64, 64), 'upscale': True, 'KEY': 'def'},
            },
        }

    def test_add_to_queue(self):
        self.queue.add_to_queue(self.example_action)
        action_obj = models.Action.objects.get()
        self.assertEqual(action_obj.data, self.example_action)

    def test_processing_match(self):
        key = 'abc'
        models.Processing.objects.create(pk=key)
        self.assertTrue(self.queue.processing(key))

    def test_processing_no_match(self):
        self.assertFalse(self.queue.processing('abc'))

    def test_processing_list(self):
        ab = models.Processing.objects.create(pk='ab')
        ef = models.Processing.objects.create(pk='ef')
        self.assertTrue(
            self.queue.processing_list('ab', 'cd', 'ef'),
            [ab.time, False, ef.time])

    def test_start_processing(self):
        self.queue.get_keys = mock.Mock(return_value=['ab', 'cd'])
        self.queue.start_processing(self.example_action)
        self.assertTrue(self.queue.get_keys.called)
        self.assertEqual(
            list(models.Processing.objects.items_list('pk', flat=True)),
            ['ab', 'cd'])

    def test_start_processing_overwrite(self):
        ab = models.Processing.objects.create(pk='ab')
        self.queue.get_keys = mock.Mock(return_value=['ab', 'cd'])
        self.queue.start_processing(self.example_action)
        self.assertEqual(
            list(models.Processing.objects.items_list('pk', flat=True)),
            ['ab', 'cd'])
        self.assertNotEqual(ab, models.Processing.objects.get(pk='ab'))

    def test_start_processing_keys_provided(self):
        self.queue.get_keys = mock.Mock()
        self.queue.start_processing(self.example_action, keys=['ab', 'cd'])
        self.assertFalse(self.queue.get_keys.called)
        self.assertEqual(
            list(models.Processing.objects.items_list('pk', flat=True)),
            ['ab', 'cd'])

    def test_finished_processing(self):
        models.Processing.objects.bulk_create([
            models.Processing(pk='ab'),
            models.Processing(pk='ef'),
        ])
        self.queue.get_keys = mock.Mock(return_value=['ab', 'cd'])
        self.queue.finished_processing(self.example_action)
        self.assertTrue(self.queue.get_keys.called)
        self.assertEqual(
            list(models.Processing.objects.items_list('pk', flat=True)),
            ['ef'])

    def test_finished_processing_keys_provided(self):
        models.Processing.objects.bulk_create([
            models.Processing(pk='ab'),
            models.Processing(pk='ef'),
        ])
        self.queue.get_keys = mock.Mock()
        self.queue.finished_processing(self.example_action, keys=['ab', 'cd'])
        self.assertFalse(self.queue.get_keys.called)
        self.assertEqual(
            list(models.Processing.objects.items_list('pk', flat=True)),
            ['ef'])
