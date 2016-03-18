"""
Storage uses ledger.processing to determine if local fallback storage
should be used rather than the default storage.

This means every check of the URL needs to check the processing state, so
there's some overhead!
"""

import re

from django.core.files.storage import default_storage, FileSystemStorage
from easy_images.engine.default import default_engine

local_storage = FileSystemStorage()


class LocalProcessingStorage(object):
    upstream_storage = default_storage
    local_storage = local_storage
    engine = default_engine
    hash_re = re.compile(r'\b([a-z0-9]{27})\.(?:jpg|png)$')

    def pick_storage(self, name):
        if isinstance(name, tuple):
            return name[:2]
        if self.is_processing(name):
            storage = self.local_storage
        else:
            storage = self.upstream_storage
        return storage, name

    def get_key(self, name):
        match = self.hash_re.search(name)
        if match:
            return match.groups(1)

    def is_processing(self, name):
        key = self.get_key(name)
        if not key:
            return False
        return self.engine.processing(key)

    def _open(self, name, *args, **kwargs):
        storage, name = self.pick_storage(name)
        return storage._open(name, *args, **kwargs)
