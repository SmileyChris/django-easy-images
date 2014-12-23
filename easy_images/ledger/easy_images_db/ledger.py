import collections
import json

from django.utils import six
from easy_images.cache import image_cache
from easy_images.ledger.base import BaseLedger

from . import models


class DBLedger(BaseLedger):

    def meta(self, source_path, opts, image_hash=None, **kwargs):
        """
        Retrieve the meta data for a processed image via a database query.
        """
        if image_hash is None:
            image_hash = self.hash(source_path, opts)
        try:
            image = models.ProcessedImage.objects.get(pk=image_hash)
        except models.ProcessedImage.DoesNotExist:
            return None
        return image.meta_json

    def meta_list(self, sources, **kwargs):
        """
        Return a list of meta data dictionaries for the sources, using a single
        database query.
        """
        hashes = kwargs.get('hashes')
        if hashes is None:
            hashes = (
                self.hash(source_path, opts) for source_path, opts in sources)
        json_dict = kwargs.get('json_dict')
        if not json_dict:
            json_dict = collections.defaultdict(None)
        if hashes:
            images = models.ProcessedImage.objects.filter(pk__in=hashes)
            for pk, meta, date in images.values_list('pk', 'meta', 'created'):
                json_dict[pk] = (meta, date)
        return [
            models.meta_json(*json_dict[image_hash])
            for image_hash in hashes]

    def save(self, source_path, opts, **kwargs):
        """
        Save a reference of a processed image to the database.
        """
        image_hash = kwargs.get('image_hash')
        if image_hash is None:
            image_hash = self.hash(source_path, opts)
        meta = kwargs.get('meta')
        if meta is None:
            meta = self.build_meta(**kwargs)
        # Remove date from meta because it is saved separately on the
        # ProcessedImage model.
        meta.pop('date')
        meta_text = json.dumps(meta)
        image = models.ProcessedImage(pk=image_hash, meta=meta_text)
        image.save()
        return image


class CachedDBLedger(DBLedger):

    def meta(self, source_path, opts, **kwargs):
        image_hash = self.hash(source_path, opts)
        meta = models.json_dict(image_cache.get(image_hash))
        if meta is not None:
            return meta
        kwargs['image_hash'] = image_hash
        meta = super(CachedDBLedger, self).meta(source_path, opts, **kwargs)
        image_cache.set(image_hash, json.dumps(meta), timeout=None)
        return meta

    def meta_list(self, sources, **kwargs):
        hashes = kwargs.get('hashes')
        if hashes is None:
            hashes = set(
                self.hash(source_path, opts) for source_path, opts in sources)
        else:
            hashes = set(hashes)
        if hashes:
            images_meta = six.iteritems(image_cache.get_many(hashes))
        else:
            images_meta = ()
        json_dict = collections.defaultdict(None, images_meta)
        add_to_cache = []
        for key, value in six.iteritems(json_dict):
            if value is None:
                add_to_cache.append(value)
            else:
                hashes.remove(key)
        kwargs['hashes'] = hashes
        kwargs['json_dict'] = json_dict
        meta_list = super(CachedDBLedger, self).meta_list(sources, **kwargs)
        # Add items found in DB into the cache.
        meta_not_cached = {}
        for key in add_to_cache:
            value = meta_list.get(key)
            if value is not None:
                meta_not_cached[key] = value
        if meta_not_cached:
            image_cache.set_many(meta_not_cached, timeout=None)
        return meta_list

    def save(self, source_path, opts, **kwargs):
        image_hash = self.hash(source_path, opts)
        meta = self.build_meta(**kwargs)
        image_cache.set(image_hash, json.dumps(meta), timeout=None)
        kwargs['meta'] = meta
        return super(CachedDBLedger, self).save(source_path, opts, **kwargs)
