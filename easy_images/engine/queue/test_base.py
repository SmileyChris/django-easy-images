from unittest import TestCase

import mock

from . import base


class BaseQueueTest(TestCase):

    def setUp(self):
        self.queue = base.BaseQueue()
        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'all_opts': {
                'easy_images/fit.jpg': {'fit': (200, 0), 'KEY': '1234'},
                'easy_images/crop.jpg': {
                    'crop': (64, 64), 'upscale': True, 'KEY': '5678'},
            },
        }

    def test_add(self):
        standard_priorities = [
            base.PRIORITY_HIGH, base.PRIORITY_NORMAL, base.PRIORITY_LOW]

        self.queue.add_to_queue = mock.Mock(return_value='queued')
        self.queue.start_processing = mock.Mock()
        self.queue.finished_processing = mock.Mock()
        for priority in standard_priorities:
            self.assertEqual(
                self.queue.add(action=self.example_action, priority=priority),
                'queued')
        self.assertEqual(
            self.queue.add_to_queue.call_count, len(standard_priorities))
        self.assertEqual(
            self.queue.start_processing.call_count, len(standard_priorities))
        self.assertEqual(self.queue.finished_processing.call_count, 0)

    def test_add_critical(self):
        self.queue.generate_and_record = mock.Mock(return_value='generated')
        self.queue.add_to_queue = mock.Mock(return_value='queued')
        self.queue.start_processing = mock.Mock()
        self.queue.finished_processing = mock.Mock()
        self.assertEqual(
            self.queue.add(
                action=self.example_action, priority=base.PRIORITY_CRITICAL),
            'generated')
        self.assertEqual(self.queue.generate_and_record.call_count, 1)
        self.assertFalse(self.queue.add_to_queue.called)
        self.assertEqual(self.queue.start_processing.call_count, 1)
        self.assertEqual(self.queue.finished_processing.call_count, 1)

    def test_finished_processing(self):
        self.queue.finished_processing(action=self.example_action)

    def test_get_keys(self):
        result = self.queue.get_keys(action=self.example_action)
        self.assertEqual(set(result), set(['1234', '5678']))
