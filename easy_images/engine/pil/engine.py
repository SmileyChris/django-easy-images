from PIL import Image, ImageFilter, ImageChops
from django.utils.functional import cached_property
from easy_images.engine.base import BaseEngine
from easy_images.engine.engine_image import BaseEngineImage

from . import utils


def _compare_entropy(start_slice, end_slice, slice, difference):
    """
    Calculate the entropy of two slices (from the start and end of an axis),
    returning a tuple containing the amount that should be added to the start
    and removed from the end of the axis.
    """
    start_entropy = utils.image_entropy(start_slice)
    end_entropy = utils.image_entropy(end_slice)
    if end_entropy and abs(start_entropy / end_entropy - 1) < 0.01:
        # Less than 1% difference, remove from both sides.
        if difference >= slice * 2:
            return slice, slice
        half_slice = slice // 2
        return half_slice, slice - half_slice
    if start_entropy > end_entropy:
        return 0, slice
    else:
        return slice, 0


class PILEngineImage(BaseEngineImage):

    @cached_property
    def transparent(self):
        return utils.is_transparent(self.image)

    @cached_property
    def exif_orientation(self):
        return utils.get_exif_orientation(self.image)

    @property
    def mode(self):
        if self.image.mode == 'I':
            return 'L'
        return self.image.mode

    def bytes(self, filename):
        """
        Save a PIL image to a bytestring.
        """
        return utils.save(filename, self.image, self.opts)

    def convert_mode(self, mode):
        image = self.image
        if image.mode == mode:
            return self
        image = utils.convert_16bit_greyscale(image)
        if image.mode != mode:
            image = image.convert(mode)
        return self.new_engine_image(image)

    def replace_alpha(self, color):
        if not self.transparent:
            return self
        if self.image.mode != 'RGBA':
            self.image.convert_mode('RGBA')
        base = Image.new('RGBA', self.image.size, color)
        base.paste(self.image, mask=self.image)
        return self.new_engine_image(base)

    def resize(self, size, antialias=True):
        kwargs = {}
        if size == self.size:
            return self
        if antialias:
            kwargs['resample'] = Image.ANTIALIAS
        image = self.image.resize(size, **kwargs)
        return self.new_engine_image(image)

    def crop(self, box):
        size = (box[2] - box[0], box[3] - box[1])
        if size == self.size:
            return self
        image = self.image.crop(box)
        return self.new_engine_image(image)

    def canvas(self, size):
        x, y = self.size
        x1, y1 = size[0]-x // 2, size[1]-y // 2
        background = (255,) * len(self.mode)
        image = Image.new(self.mode, size, background)
        image.paste(self.image, (x1, y1))
        return self.new_engine_image(image)

    def filter_detail(self, image, value):
        if not value:
            return
        return image.filter(ImageFilter.DETAIL)

    def filter_sharpen(self, image, value):
        if not value:
            return
        return image.filter(ImageFilter.SHARPEN)

    def filter_autocrop(self, image, value):
        if not value:
            return
        # If transparent, flatten.
        if utils.is_transparent(image) and False:
            no_alpha = Image.new('L', image.size, (255))
            no_alpha.paste(image, mask=image.split()[-1])
        else:
            no_alpha = image.convert('L')
        # Convert to black and white image.
        bw = no_alpha.convert('L')
        # White background.
        bg = Image.new('L', image.size, 255)
        bbox = ImageChops.difference(bw, bg).getbbox()
        if bbox:
            return image.crop(bbox)

    def smart_crop(self, target):
        source_x, source_y = self.size
        diff_x, diff_y = source_x - target[0], source_y - target[1]
        if diff_x <= 0 and diff_y <= 0:
            return self
        left = top = 0
        right, bottom = self.size
        while diff_x > 0:
            slice = min(diff_x, max(diff_x // 5, 10))
            start = self.image.crop((left, 0, left + slice, source_y))
            end = self.image.crop((right - slice, 0, right, source_y))
            add, remove = _compare_entropy(start, end, slice, diff_x)
            left += add
            right -= remove
            diff_x = diff_x - add - remove
        while diff_y > 0:
            slice = min(diff_y, max(diff_y // 5, 10))
            start = self.image.crop((0, top, source_x, top + slice))
            end = self.image.crop((0, bottom - slice, source_x, bottom))
            add, remove = _compare_entropy(start, end, slice, diff_y)
            top += add
            bottom -= remove
            diff_y = diff_y - add - remove
        return self.crop((left, top, right, bottom))


class Engine(BaseEngine):
    """
    Easy Images engine to generate images using PIL.
    """
    exif_orientation = True

    def get_image_class(self, opts):
        return PILEngineImage

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
