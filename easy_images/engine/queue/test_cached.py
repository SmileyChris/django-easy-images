from unittest import TestCase

import mock

from . import cached


class BaseTest(TestCase):

    def setUp(self):

        # Build the engine inside setup so the mocks are reset for every test.
        class FakeEngine(object):
            _processing = mock.Mock(return_value='ABC')
            _processing_list = mock.Mock(
                side_effect=lambda keys: [key.upper() for key in keys])

            def processing(self, *args, **kwargs):
                return self._processing(*args, **kwargs)

            def processing_list(self, *args, **kwargs):
                return self._processing_list(*args, **kwargs)

            start_processing = mock.Mock()
            finished_processing = mock.Mock()


        class TestObj(cached.CachedProcessingMixin, FakeEngine):
            pass

        self.engine_class = FakeEngine
        self.obj = TestObj()

        self.example_action = {
            'source': 'easy_images/fake.jpg',
            'all_opts': {
                'easy_images/fit.jpg': {'fit': [200, 0], 'KEY': 'abc'},
                'easy_images/crop.jpg': {
                    'crop': [64, 64], 'upscale': True, 'KEY': 'def'},
            },
        }


class ProcessingTest(BaseTest):

    def test_standard(self):
        key = 'ptts'
        output = self.obj.processing(key=key)
        self.assertEqual(output, 'ABC')
        self.engine_class._processing.assert_called_with(key)

    def test_only_cache(self):
        self.obj.only_cache = True
        key = 'pttoc'
        output = self.obj.processing(key=key)
        self.assertFalse(output)
        self.assertFalse(self.engine_class._processing.called)

    def test_cached(self):
        key = 'pttc'
        cache_key = 'easy_image_queue:{0}'.format(key)
        cached.image_cache.set(cache_key, True, timeout=None)
        try:
            output = self.obj.processing(key=key)
            self.assertEqual(output, True)
            self.assertFalse(self.engine_class._processing.called)
        finally:
            cached.image_cache.delete(cache_key)


class ProcessingListTest(BaseTest):

    def test_standard(self):
        output = self.obj.processing_list(['a', 'b', 'c'])
        self.assertEqual(output, ['A', 'B', 'C'])

    def test_only_cache(self):
        self.obj.only_cache = True
        output = self.obj.processing_list(['a', 'b', 'c'])
        self.assertEqual(output, [False, False, False])
        self.assertFalse(self.engine_class._processing_list.called)

    def test_cached(self):
        keys = ['a', 'b', 'c']
        cache_keys = ['easy_image_queue:{0}'.format(key) for key in keys]
        cached.image_cache.set(cache_keys[0], 'XXX')
        cached.image_cache.set(cache_keys[2], False)
        try:
            output = self.obj.processing_list(['a', 'b', 'c'])
            self.engine_class._processing_list.assert_called_with(['b'])
            self.assertEqual(output, ['XXX', 'B', False])
        finally:
            cached.image_cache.delete(cache_keys[0])
            cached.image_cache.delete(cache_keys[2])


class StartFinishedProcessingTest(BaseTest):

    def test_start_processing(self):
        keys = ['ab', 'cd']
        self.obj.get_keys = mock.Mock(return_value=keys)
        cache_keys = [
            '{0}{1}'.format(self.obj.cache_prefix, key) for key in keys]
        try:
            self.obj.start_processing(self.example_action)
            for key in cache_keys:
                self.assertTrue(
                    cached.image_cache.get(key),
                    'Expected to find {0} in cache'.format(key))
            self.engine_class.start_processing.assert_called_with(
                action=self.example_action, keys=keys)
        finally:
            for key in cache_keys:
                cached.image_cache.delete(key)

    def test_finished_processing(self):
        keys = ['ab', 'cd']
        self.obj.get_keys = mock.Mock(return_value=keys)
        cache_keys = [
            '{0}{1}'.format(self.obj.cache_prefix, key) for key in keys]
        cached.image_cache.set(cache_keys[1], True)
        try:
            self.obj.finished_processing(self.example_action)
            for key in cache_keys:
                self.assertFalse(
                    cached.image_cache.get(key),
                    "Shouldn't find {0} in cache".format(key))
        finally:
            for key in cache_keys:
                cached.image_cache.delete(key)
