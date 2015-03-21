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

    def generate(self, action):
        if not action.get('all_opts'):
            return {}
        opts = action['all_opts'].values()[0]
        source_obj = self.get_source(action['source'], opts)
        source_image = self.build_source(source_obj)
        if not source_image:
            return {}
        images = {}
        for output_target, opts in action['all_opts'].items():
            image = source_image
            for processor in self.get_processors():
                image = processor(image, **opts)
            output_file = self.write_image(
                image, output_target, destination=None, **opts)
            self.save(output_target, output_file, opts)
            images[output_target] = image
        return images

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
