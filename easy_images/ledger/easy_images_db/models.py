from __future__ import unicode_literals
import json

from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


def meta_json(meta_text, date=None):
    """
    A dictionary of meta data from a JSON string.

    If ``meta_text`` is None, None will be returned. Otherwise the return value
    is guaranteed to be a dictionary.

    :rtype: dict, None
    """
    if meta_text is None:
        return None
    try:
        data = json.loads(meta_text)
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if date:
        if not timezone.is_aware(date):
            date = timezone.make_aware(date, timezone.get_current_timezone())
        date = timezone.make_naive(date, timezone.utc)
        data['date'] = date.isoformat()
    return data


@python_2_unicode_compatible
class ProcessedImage(models.Model):
    hash = models.CharField(max_length=28, primary_key=True)
    src_hash = models.CharField(max_length=28)
    opts_hash = models.CharField(max_length=28)
    created = models.DateTimeField(default=timezone.now)
    meta = models.TextField()

    def __str__(self):
        return self.hash

    @property
    def meta_json(self):
        """
        A dictionary of meta data for this image.

        :rtype: dict
        """
        return meta_json(self.meta, date=self.created)
