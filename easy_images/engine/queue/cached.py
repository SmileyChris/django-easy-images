from django.utils import six
from easy_images.cache import image_cache


class CachedProcessingMixin(object):
    only_cache = False
    cache_prefix = 'easy_image_queue:'

    def processing(self, key, **kwargs):
        value = image_cache.get(self.cache_prefix + key)
        if value:
            return value
        if self.only_cache:
            return False
        return super(CachedProcessingMixin, self).processing(key)

    def processing_list(self, keys):
        cache_keys = (self.cache_prefix + key for key in keys)
        cache_prefix_len = len(self.cache_prefix)
        found = dict(
            (key[cache_prefix_len:], value)
            for key, value in six.iteritems(image_cache.get_many(cache_keys)))
        if not self.only_cache:
            not_found = list(set(keys) - set(found))
            if not_found:
                upstream = super(CachedProcessingMixin, self).processing_list(
                    not_found)
                for key, processing in zip(not_found, upstream):
                    if processing:
                        found[key] = processing
        return [found.get(key, False) for key in keys]

    def start_processing(self, action, keys=None, **kwargs):
        if keys is None:
            keys = self.get_keys(action)
        image_cache.set_many(
            dict((self.cache_prefix + key, True) for key in keys),
            timeout=None)
        if not self.only_cache:
            super(CachedProcessingMixin, self).start_processing(
                action=action, keys=keys, **kwargs)

    def finished_processing(self, action, keys=None, **kwargs):
        if keys is None:
            keys = self.get_keys(action)
        image_cache.delete_many(self.cache_prefix + key for key in keys)
        if not self.only_cache:
            super(CachedProcessingMixin, self).finished_processing(
                action=action, keys=keys, **kwargs)
