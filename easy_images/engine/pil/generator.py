import PIL
from easy_images.engine.pil import processors

from .output import PILOutput


class PILGenerator(PILOutput):
    """
    Easy Images engine mixin to generate images.
    """
    default_processors = (
        processors.colorspace,
        processors.autocrop,
        processors.scale_and_crop,
        processors.filters,
        processors.background,
    )

    def get_processors(self):
        return self.default_processors

    def generate(self, action):
        source_obj = self.get_source(action['source'])
        source_image = self.build_source(source_obj)
        if not source_image:
            return []
        images = []
        for output_target, opts in action['all_opts'].items():
            image = source_image
            for processor in self.get_processors():
                image = processor(image, **opts)
            self.save(image, output_target, opts)
            images.append(image)
        return images

    def build_source(self, source_obj):
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
        return image
