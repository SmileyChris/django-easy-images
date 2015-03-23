"""
An engine's job is to process actions sent to it.

It may do this in a queue, or in-process depending on the requirements.

An action looks like this::

    {
        "source": source_url_or_path,
        "ledger": current_ledger,
        "opts": [
            {
                'fit': (200, 0),
                'FILENAME': '...',
                'FILENAME_TRANSPARENT': '...',
            },
            {
                'crop': (64, 64),
                'upscale': True,
                'FILENAME': '...',
            },
        ]
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

    def generate(self, action):
        """
        Generate image(s) and save to storage.
        """
        if not action.get('opts'):
            return {}
        opts = action['opts'][0]
        source_file = self.get_source_file(action['source'], opts)
        source_image = self.build_source(source_file)
        if not source_image:
            return {}
        images = {}
        for opts in action['opts']:
            image = self.process_image(source_image, opts)
            if 'FILENAME_TRANSPARENT' in opts and self.is_transparent(image):
                filename = opts['FILENAME_TRANSPARENT']
            else:
                filename = opts['FILENAME']
            processed_file = self.write_image(image, filename, **opts)
            self.save(filename, processed_file, opts)
            images[filename] = image
        return images

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
        for opts in action['opts']:
            if images:
                image = images.get(opts['FILENAME'])
                if image is None and 'FILENAME_TRANSPARENT' in opts:
                    image = images.get(opts['FILENAME_TRANSPARENT'])
            else:
                image = None
            self.record(source_path, opts, ledger, image)
        return images

    def record(self, source_path, opts, ledger, image):
        meta = self.build_meta(image)
        return ledger.save(source_path, opts, meta)

    @abc.abstractmethod
    def build_meta(self, image):
        """
        Build a dictionary of metadata for an image.
        """

    @abc.abstractmethod
    def build_source(self, source_file):
        """
        Build the source image.
        """

    @abc.abstractmethod
    def process_image(self, source_image, opts):
        """
        Process the source image using the options provided.
        """

    @abc.abstractmethod
    def is_transparent(self, image):
        """
        Check whether the image is transparent.

        :rtype: boolean
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

    def get_source_file(self, source, opts):
        """
        The source file.

        :rtype: file-like object
        """
        if hasattr(source, 'read'):
            # Quacks like a file-like object, use it directly.
            return source
        storage = self.get_source_storage(opts)
        return storage.open(source)

    def get_generated_file(self, source_path, opts):
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
