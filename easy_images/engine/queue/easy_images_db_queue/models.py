from __future__ import unicode_literals
import json

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from easy_images.engine.queue.base import PRIORITY_NORMAL

from . import managers


@python_2_unicode_compatible
class Processing(models.Model):
    """
    Model to keep track of options that are being processed.
    """
    key = models.CharField(max_length=28, primary_key=True)
    time = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('time',)

    def __str__(self):
        return self.key


@python_2_unicode_compatible
class Action(models.Model):
    """
    Model defining an action for an Easy Image engine.
    """
    action = models.TextField()
    time = models.DateTimeField(default=timezone.now)
    priority = models.PositiveSmallIntegerField(default=PRIORITY_NORMAL)

    objects = managers.ActionManager()

    class Meta:
        verbose_name = 'Queued Action'
        index_together = [
            ('priority', 'time'),
        ]
        ordering = ('-priority', 'time')

    def __str__(self):
        return "Queue for {source}".format(
            source=self.data.get('source') or "(unknown)")

    @property
    def data(self):
        """
        A dictionary that describes this action.

        :rtype: dict
        """
        try:
            data = json.loads(self.action)
        except ValueError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data
