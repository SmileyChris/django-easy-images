"""
Get the django cache for easy images.

Usage::

    from easy_images.cache import image_cache
    ...
"""

from django.core.cache.backends.base import InvalidCacheBackendError
from django.core.cache import caches


try:
    image_cache = caches['easy_images']
except InvalidCacheBackendError:
    from django.core.cache import cache as image_cache   # noqa
