import json

from django.db import IntegrityError
from django.utils import six
from easy_images.cache import image_cache
from easy_images.ledger.base import BaseLedger

from easy_images_db_ledger import models


class DBLedger(BaseLedger):

    def meta(self, source_path, opts, image_hash=None, **kwargs):
        """
        Retrieve the meta data for a processed image via a database query.
        """
        if image_hash is None:
            image_hash = self.get_filename_info(source_path, opts).hash
        try:
            image = (
                models.ProcessedImage.objects.filter(pk=image_hash)
                .only('meta', 'created'))[0]
        except IndexError:
            return None
        return image.meta_json

    def meta_list(self, sources, **kwargs):
        """
        Return a list of meta data dictionaries for the sources, using a single
        database query.
        """
        hashes = kwargs.get('hashes')
        if hashes is None:
            hashes = [
                self.get_filename_info(source_path, opts).hash
                for source_path, opts in sources]
        json_dict = kwargs.get('json_dict') or {}
        missing_hashes = set(hashes) - set(json_dict)
        if missing_hashes:
            images = models.ProcessedImage.objects.filter(
                pk__in=missing_hashes)
            for pk, meta, date in images.values_list('pk', 'meta', 'created'):
                json_dict[pk] = models.meta_json(meta, date)
        return [json_dict.get(image_hash) for image_hash in hashes]

    def save(self, source_path, opts, meta, **kwargs):
        """
        Save a reference of a processed image to the database.
        """
        filename_info = kwargs.get('filename_info')
        if filename_info is None:
            filename_info = self.get_filename_info(source_path, opts)

        # Remove date from meta because it is saved separately on the
        # ProcessedImage model.
        meta.pop('date', None)
        meta_text = json.dumps(meta)
        image = models.ProcessedImage(
            pk=filename_info.hash, meta=meta_text,
            opts_hash=filename_info.opts_hash,
            src_hash=filename_info.src_hash)
        try:
            image.save(force_insert=True)
        except IntegrityError:
            # The more unlikely case that the hash already exists, we'll
            # standard save it to update the row instead.
            image.save(force_insert=True)
        return image


class CachedDBLedger(DBLedger):

    def meta(self, source_path, opts, image_hash=None, **kwargs):
        if image_hash is None:
            image_hash = self.get_filename_info(source_path, opts).hash
        meta = models.meta_json(image_cache.get(image_hash))
        if meta is not None:
            return meta
        kwargs['image_hash'] = image_hash
        meta = super(CachedDBLedger, self).meta(source_path, opts, **kwargs)
        image_cache.set(image_hash, json.dumps(meta), timeout=None)
        return meta

    def meta_list(self, sources, **kwargs):
        hashes = kwargs.get('hashes')
        if hashes is None:
            hashes = [
                self.get_filename_info(source_path, opts).hash
                for source_path, opts in sources]
        json_dict = {}
        if hashes:
            json_dict.update(six.iteritems(image_cache.get_many(hashes)))
        add_to_cache = []
        for i, key in enumerate(hashes):
            value = json_dict.get(key)
            if value is None:
                add_to_cache.append(i)
        kwargs['hashes'] = hashes
        kwargs['json_dict'] = json_dict
        meta_list = super(CachedDBLedger, self).meta_list(sources, **kwargs)
        # Add items found in DB into the cache.
        meta_not_cached = {}
        for i in add_to_cache:
            value = meta_list[i]
            if value is not None:
                meta_not_cached[hashes[i]] = value
        if meta_not_cached:
            image_cache.set_many(meta_not_cached, timeout=None)
        return meta_list

    def save(self, source_path, opts, meta, **kwargs):
        filename_info = kwargs.get('filename_info')
        if filename_info is None:
            filename_info = self.get_filename_info(source_path, opts)
        image_cache.set(filename_info.hash, meta, timeout=None)
        kwargs['filename_info'] = filename_info
        return super(CachedDBLedger, self).save(
            source_path=source_path, opts=opts, meta=meta, **kwargs)
