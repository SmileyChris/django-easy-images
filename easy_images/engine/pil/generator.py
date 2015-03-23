import PIL
from easy_images.engine.pil import processors

from . import output, utils


class PILGenerator(output.PILOutput):
    """
    Easy Images engine mixin to generate images.
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

    def build_source(self, source_obj):
        if hasattr(source_obj, 'seek'):
            source_obj.seek(0)
        image = PIL.Image.open(source_obj)

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

    def process_image(self, source_image, opts):
        image = source_image
        for processor in self.get_processors():
            image = processor(image, **opts)
        return image

    def is_transparent(self, image):
        return utils.is_transparent(image)
