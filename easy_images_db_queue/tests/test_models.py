from django.test import TestCase
import mock

from easy_images.engine.queue.base import PRIORITY_HIGH, PRIORITY_LOW

from .. import models


class ProcessingTest(TestCase):

    def test_text(self):
        obj = models.Processing(key='this')
        self.assertEqual('{0}'.format(obj), 'this')


class ActionTest(TestCase):

    def test_text(self):
        obj = models.Action(action='blah')
        patch = mock.patch.object(
            models.Action, 'data', new_callable=mock.PropertyMock)
        with patch as patched_model:
            patched_model.return_value = {'source': 'TEST'}
            output = '{0}'.format(obj)
        self.assertEqual(output, 'Queue for TEST')

    def test_text_no_source(self):
        obj = models.Action(action='blah')
        patch = mock.patch.object(
            models.Action, 'data', new_callable=mock.PropertyMock)
        with patch as patched_model:
            patched_model.return_value = {}
            output = '{0}'.format(obj)
        self.assertEqual(output, 'Queue for (unknown)')

    def test_invalid_data(self):
        obj = models.Action(action='invalid')
        self.assertEqual(obj.data, {})
        obj = models.Action(action='["not a dict"]')
        self.assertEqual(obj.data, {})

    def test_valid_data(self):
        obj = models.Action(action='{"test": 1, "second": true}')
        self.assertEqual(obj.data, {'test': 1, 'second': True})

    def test_ordering(self):
        l1 = models.Action.objects.create(priority=PRIORITY_LOW)
        n1 = models.Action.objects.create()
        h1 = models.Action.objects.create(priority=PRIORITY_HIGH)
        l2 = models.Action.objects.create(priority=PRIORITY_LOW)
        h2 = models.Action.objects.create(priority=PRIORITY_HIGH)
        n2 = models.Action.objects.create()
        self.assertEqual(
            list(models.Action.objects.all()), [h1, h2, n1, n2, l1, l2])


class ActionManagerTest(TestCase):

    def test_queue(self):
        self.assertTrue(models.Action.objects.queue.alters_data)
        a1 = models.Action.objects.create(data='1')
        a2 = models.Action.objects.create(data='2')
        self.assertEqual(list(models.Action.objects.queue()), [a1, a2])

    def test_pop(self):
        self.assertTrue(models.Action.objects.pop.alters_data)
        a1 = models.Action.objects.create(data='1')
        a2 = models.Action.objects.create(data='2')
        self.assertEqual(models.Action.objects.pop(), a1)
        self.assertEqual(list(models.Action.objects.all()), [a2])
        self.assertEqual(models.Action.objects.pop(), a2)
        self.assertEqual(list(models.Action.objects.all()), [])
        self.assertEqual(models.Action.objects.pop(), None)
