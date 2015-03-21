"""
An engine's job is to process actions sent to it.

It may do this in a queue, or in-process depending on the requirements.

An action looks like this::

    {
        "source": source_url_or_path,
        "ledger": current_ledger,
        "all_opts": {
            output_path: {'fit': (200, 0), 'KEY': '...'},
            output_path: {'crop': (64, 64), 'upscale': True, 'KEY': '...'},
        }
    }
"""
import abc

from django.core.files import File
from django.utils import six

from easy_images.ledger.default import default_ledger, import_string


@six.add_metaclass(abc.ABCMeta)
class BaseEngine(object):

    def add(self, action, **kwargs):
        """
        Standard way of adding an action to be processed by the engine.

        If the images are generated in-process, they should be returned.
        """
        return self.generate_and_record(action)

    @abc.abstractmethod
    def generate(self, action):
        """
        Generate image(s) and save to storage.
        """

    def generate_and_record(self, action):
        """
        Generate processed images, save them to storage, then record the change
        in the ledger.
        """
        ledger = action.get('ledger')
        if ledger:
            ledger = import_string(ledger)()
        else:
            ledger = default_ledger

        images = self.generate(action)
        source_path = action['source']
        for output_target, opts in action['all_opts'].items():
            image = images.get(output_target) if images else None
            self.record(source_path, opts, ledger, image)
        return images

    def record(self, source_path, opts, ledger, image):
        if not opts.get('KEY'):
            return
        meta = self.build_meta(image)
        return ledger.save(source_path, opts, meta)

    @abc.abstractmethod
    def build_meta(self, image):
        """
        Build a dictionary of metadata for an image.
        """

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

    def processing_url(self, source_path, opts, source_url, **kwargs):
        """
        URL to return for an image which is currently being processed.
        """
        raise NotImplementedError()

    def get_source(self, source, opts):
        """
        The source file.

        :rtype: file-like object
        """
        if hasattr(source, 'read'):
            # Quacks like a file-like object, use it directly.
            return source
        storage = self.get_source_storage(opts)
        return storage.open(source)

    def get_generated(self, source_path, opts):
        """
        Get the generated file.
        """
        storage = self.get_generated_storage(opts)
        return storage.open(source_path)

    def get_source_storage(self, opts):
        import django.core.files.storage
        return django.core.files.storage.default_storage

    def get_generated_storage(self, opts):
        import easy_images.engine.default
        return easy_images.engine.default.default_storage

    def save(self, path, obj, opts):
        """
        Save data from file-like ``obj`` to a relative path.
        """
        return self.get_generated_storage(opts).save(path, File(obj))

    # def clean_opts(opts, remove_upper=False, **kwargs):
    #     """
    #     Return a cleaned of the options.
    #     """
    #     if not remove_upper:
    #         return opts
    #     return dict((key, value) for key, value in opts if key != key.upper())
