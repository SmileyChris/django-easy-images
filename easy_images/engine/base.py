"""
An engine's job is to process actions sent to it.

It may do this in a queue, or in-process depending on the requirements.

An action looks like this::

    {
        "source": source_url_or_path,
        "all_opts": {
            output_path: {'fit': (200, 0), 'KEY': '...'},
            output_path: {'crop': (64, 64), 'upscale': True, 'KEY': '...'},
        }
    }
"""
from django.core.files import File

from .default import default_storage


class BaseEngine(object):

    def add(self, action, **kwargs):
        """
        Standard way of adding an action to be processed by the engine.

        If the image is generated in-process, it should be returned.
        """
        return self.generate(action)

    def generate(self, action):
        """
        Generate image(s).
        """
        raise NotImplementedError()

    def processing(self, key, **kwargs):
        """
        Whether the image with the hashed key is currently being generated (or
        is queued for processing).

        The base behaviour is to assume the image is *not* currently being
        generated.

        :rtype: boolean
        """
        return False

    def processing_list(self, keys):
        """
        Check the processing status for multiple images.

        Some backends may be able to use this to increase efficiency when
        dealing with bulk actions.
        """
        processing = []
        for key in keys:
            processing.append(self.processing(key))
        return processing

    def processing_url(self, source_path, opts, url, **kwargs):
        """
        URL to return for an image which is currently being processed.
        """
        return ''

    def get_source(self, source, opts):
        """
        The source file.

        :rtype: file-like object
        """
        if hasattr(source, 'read'):
            # Quacks like a file-like object, use it directly.
            return source
        storage = self.get_source_storage(opts)
        storage.open(source)

    def get_generated(self, source, opts):
        """
        Get the generated file.
        """
        storage = self.get_generated_storage(opts)
        return storage.open(source)

    def get_source_storage(self, opts):
        import django.core.files.storage
        return django.core.files.storage.default_storage

    def get_generated_storage(self, opts):
        return default_storage

    def save(self, path, obj):
        """
        Save data from file-like ``obj`` to a relative path.
        """
        return self.get_generated_storage().save(path, File(obj))

    # def clean_opts(opts, remove_upper=False, **kwargs):
    #     """
    #     Return a cleaned of the options.
    #     """
    #     if not remove_upper:
    #         return opts
    #     return dict((key, value) for key, value in opts if key != key.upper())
