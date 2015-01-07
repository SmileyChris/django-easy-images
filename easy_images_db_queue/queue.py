import json

from easy_images.engine.queue.base import BaseQueue
from easy_images.engine.queue.cached import CachedProcessingMixin
from django.db import transaction

from . import models


class DBQueue(BaseQueue):

    def add_to_queue(self, action, priority=None, **kwargs):
        create_kwargs = {}
        if priority is not None:
            create_kwargs['priority'] = priority
        models.Action.objects.create(
            action=json.dumps(action), **create_kwargs)

    def processing(self, key, **kwargs):
        keys = list(
            models.Processing.objects.filter(pk=key)
            .values_list('time', flat=True))
        if keys:
            return keys[0]
        return False

    def processing_list(self, keys):
        processing = dict(
            models.Processing.objects.filter(pk__in=keys)
            .values_list('pk', 'time'))
        return [processing.get(key, False) for key in keys]

    def start_processing(self, action, keys=None, **kwargs):
        if keys is None:
            keys = self.get_keys(action)
        with transaction.atomic():
            models.Processing.objects.filter(pk__in=keys).delete()
            models.Processing.objects.bulk_create(
                [models.Processing(pk=key) for key in keys])

    def finished_processing(self, action, keys=None, **kwargs):
        if keys is None:
            keys = self.get_keys(action)
        models.Processing.objects.filter(pk__in=keys).delete()


class CachedDBQueue(CachedProcessingMixin, DBQueue):
    """
    Same as :class:`DBQueue` but only uses a cache rather than the database
    for the "is processing" logic.
    """
    cache_only = True
