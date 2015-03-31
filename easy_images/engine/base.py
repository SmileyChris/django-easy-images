"""
An engine's job is to process actions sent to it.

It may do this in a queue, or in-process depending on the requirements.

An action looks like this::

    {
        "source": source_url_or_path,
        "ledger": current_ledger,
        "opts": [
            {
                'KEY': 'hash',
                'FILENAME': '...',
                'FILENAME_TRANSPARENT': '...',
                'fit': (200, 0),
            },
            {
                'KEY': 'hash',
                'FILENAME': '...',
                'crop': (64, 64),
                'upscale': True,
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

        :returns: list of processed ``EngineImage`` instances
        """
        if not action.get('opts'):
            return []
        opts = action['opts'][0]
        source_file = self.get_source_file(action['source'], opts)
        source_image = self.build_source(source_file)
        if not source_image:
            return []
        images = []
        for opts in action['opts']:
            engine_image = self.process_image(source_image, opts)
            transparent = engine_image and engine_image.transparent
            if transparent and 'FILENAME_TRANSPARENT' in opts:
                filename = opts['FILENAME_TRANSPARENT']
            else:
                filename = opts['FILENAME']
            # Save to storage.
            self.save(filename, engine_image, opts)
            images.append(engine_image)
        return images

    def generate_and_record(self, action):
        """
        Generate processed images, save them to storage, then record the change
        in the ledger.

        :returns: list of processed ``EngineImage`` instances
        """
        ledger = action.get('ledger')
        if ledger:
            ledger = import_string(ledger)()
        else:
            ledger = default_ledger
        images = self.generate(action)
        source_path = action['source']
        for i, opts in enumerate(action['opts']):
            image = images and images[i] or None
            meta = self.build_meta(image)
            ledger.save(source_path, opts, meta)
        return images

    def build_meta(self, image):
        """
        Build a dictionary of metadata for an ``EngineImage``.
        """
        if not image:
            return {}
        meta = {
            'size': image.size,
        }
        if image.transparent:
            meta['transparent'] = True

    @abc.abstractmethod
    def build_source(self, source_file):
        """
        Build the source image.
        """

    @abc.abstractmethod
    def process_image(self, source_image, opts):
        """
        Process the source image using the options provided.

        :rtype: EngineImage
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

    def save(self, path, engine_image, opts):
        """
        Save an ``EngineImage`` to a relative path.
        """
        processed_file = File(engine_image.bytes(path, opts))
        return self.get_generated_storage(opts).save(path, processed_file)

    # def clean_opts(opts, remove_upper=False, **kwargs):
    #     """
    #     Return a cleaned of the options.
    #     """
    #     if not remove_upper:
    #         return opts
    #     return dict((key, value) for key, value in opts if key != key.upper())
