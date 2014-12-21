"""
Get the django cache for easy images.

Usage::

    from easy_images.cache import image_cache
    ...
"""

from django.core.cache.backends.base import InvalidCacheBackendError

# Set up image cache.
try:
    from django.core.cache import caches
    get_cache = lambda cache_name: caches[cache_name]
except ImportError:  # Django <= 1.6
    from django.core.cache import get_cache
try:
    image_cache = get_cache('easy_images')
except InvalidCacheBackendError:
    from django.core.cache import cache as image_cache  # noqa
