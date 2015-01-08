from django.test import TestCase
import mock

from . import models


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
