from PIL import Image
from django.utils.functional import cached_property
from easy_images.engine.base import BaseEngine
from easy_images.engine.engine_image import BaseEngineImage

from . import utils, processors


class EngineImage(BaseEngineImage):

    @cached_property
    def transparent(self):
        return utils.is_transparent(self.image)

    @cached_property
    def exif_orientation(self):
        return utils.get_exif_orientation(self.image)

    def bytes(self, filename):
        """
        Save a PIL image to a bytestring.
        """
        return utils.save(filename, self.image, self.opts)


class Engine(BaseEngine):
    """
    Easy Images engine to generate images using PIL.
    """
    default_processors = (
        processors.colorspace,
        processors.autocrop,
        processors.resize,
        processors.filters,
        processors.background,
    )
    exif_orientation = True

    def get_processors(self):
        return self.default_processors

    def process_image(self, source_image, opts):
        image = source_image
        for processor in self.get_processors():
            image = processor(image, **opts)
        return EngineImage(image, opts)

    def build_source(self, source_obj):
        if hasattr(source_obj, 'seek'):
            source_obj.seek(0)
        image = Image.open(source_obj)

        # Fully load the image now to catch any problems with the image
        # contents.
        try:
            # An "Image file truncated" exception can occur for some images
            # that are still mostly valid -- we'll swallow the exception.
            image.load()
        except IOError:
            pass
        # Try a second time to catch any other potential exceptions.
        image.load()

        if self.exif_orientation:
            image = utils.exif_orientation(image)

        return image
