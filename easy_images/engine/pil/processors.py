import itertools
import re

from django.utils import six
from PIL import Image, ImageChops, ImageFilter

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


def _points_table():
    """
    Iterable to map a 16 bit grayscale image to 8 bits.
    """
    for i in range(256):
        for j in itertools.repeat(i, 256):
            yield j


def colorspace(im, bw=False, replace_alpha=False, **kwargs):
    """
    Convert images to the correct color space.

    A passive option (i.e. always processed) of this method is that all images
    (unless grayscale) are converted to RGB colorspace.

    This processor should be listed before :func:`resize` so palette is changed
    before the image is resized.

    bw
        Make the thumbnail grayscale (not really just black & white).

    replace_alpha
        Replace any transparency layer with a solid color. For example,
        ``replace_alpha='#fff'`` would replace the transparency layer with
        white.

    """
    if im.mode == 'I':
        # PIL (and pillow) have can't convert 16 bit grayscale images to lower
        # modes, so manually convert them to an 8 bit grayscale.
        im = im.point(list(_points_table()), 'L')

    is_transparent = utils.is_transparent(im)
    is_grayscale = im.mode in ('L', 'LA')
    new_mode = im.mode
    if is_grayscale or bw:
        new_mode = 'L'
    else:
        new_mode = 'RGB'

    if is_transparent:
        if replace_alpha:
            if im.mode != 'RGBA':
                im = im.convert('RGBA')
            base = Image.new('RGBA', im.size, replace_alpha)
            base.paste(im, mask=im)
            im = base
        else:
            new_mode = new_mode + 'A'

    if im.mode != new_mode:
        im = im.convert(new_mode)

    return im


def autocrop(im, autocrop=False, **kwargs):
    """
    Remove any unnecessary whitespace from the edges of the source image.

    This processor should be listed before :func:`resize` so the whitespace is
    removed from the source image before any resize takes place.

    autocrop
        Activates the autocrop method for this image.

    """
    if autocrop:
        # If transparent, flatten.
        if utils.is_transparent(im) and False:
            no_alpha = Image.new('L', im.size, (255))
            no_alpha.paste(im, mask=im.split()[-1])
        else:
            no_alpha = im.convert('L')
        # Convert to black and white image.
        bw = no_alpha.convert('L')
        # White background.
        bg = Image.new('L', im.size, 255)
        bbox = ImageChops.difference(bw, bg).getbbox()
        if bbox:
            im = im.crop(bbox)
    return im


def resize(im, fit=None, crop=None, fill=None, smart_crop=False, upscale=False,
           zoom=None, target=None, HIGHRES=None, **kwargs):
    """
    Handle resizing of the source image.

    Images can be fit / cropped against a single dimension by using zero
    as the placeholder in the size. For example, ``size=(100, 0)`` will cause
    the image to be resized to 100 pixels wide, keeping the aspect ratio of
    the source image.

    fit=(x, y)
        Proportionally scale the image (keeping the same aspect ratio) to fit
        within these dimensions.

    crop=(x, y)
        Crop the source image height or width to exactly match the requested
        thumbnail size.

    fill=(x, y)
        Proportianally scale the image so that it fills the given dimensions on
        both axis.

    smart_crop
        Use with ``crop`` incrementally crop the source image down to the
        requested size by removing slices from edges with the least entropy.

    upscale
        Allow upscaling of the source image during resizing.

    zoom=int
        A percentage to zoom in on the resized image. For example, a zoom of
        ``40`` will clip 20% off each side of the source image before
        thumbnailing.

    target=(x, y)
        Set the focal point as a percentage for the image if it needs to be
        cropped (defaults to ``(50, 50)``).

        For example, ``target="10,20"`` will set the focal point as 10% and 20%
        from the left and top of the image, respectively. If the image needs to
        be cropped, it will trim off the right and bottom edges until the focal
        point is centered.

    HIGHRES=int/float
        Multiply the target resolution by this.
    """
    size = crop or fit or fill
    if not size:
        return im

    source_x, source_y = [float(v) for v in im.size]
    target_x, target_y = [int(v) for v in size]
    if HIGHRES:
        target_x = int(target_x * HIGHRES)
        target_y = int(target_y * HIGHRES)

    if crop or fill or not target_x or not target_y:
        scale = max(target_x / source_x, target_y / source_y)
    else:
        scale = min(target_x / source_x, target_y / source_y)

    # Handle one-dimensional targets.
    if not target_x:
        target_x = source_x * scale
    if not target_y:
        target_y = source_y * scale

    if zoom:
        if not crop:
            target_x = source_x * scale
            target_y = source_y * scale
            crop = True
        scale *= (100 + int(zoom)) / 100.0

    target_x = int(round(target_x))
    target_y = int(round(target_y))

    if scale < 1.0 or (scale > 1.0 and upscale):
        # Resize the image to the target size boundary. Round the scaled
        # boundary sizes to avoid floating point errors.
        im = im.resize((int(round(source_x * scale)),
                        int(round(source_y * scale))),
                       resample=Image.ANTIALIAS)

    if crop:
        # Use integer values now.
        source_x, source_y = im.size
        # Difference between new image size and requested size.
        diff_x = int(source_x - min(source_x, target_x))
        diff_y = int(source_y - min(source_y, target_y))
        if diff_x or diff_y:
            if isinstance(target, six.string_types):
                target = re.match(r'(\d+)?,(\d+)?$', target)
                if target:
                    target = target.groups()
            if target:
                focal_point = [int(n) if (n or n == 0) else 50 for n in target]
            else:
                focal_point = 50, 50
            # Crop around the focal point
            halftarget_x, halftarget_y = int(target_x / 2), int(target_y / 2)
            focal_point_x = int(source_x * focal_point[0] / 100)
            focal_point_y = int(source_y * focal_point[1] / 100)
            box = [
                max(0, min(source_x - target_x, focal_point_x - halftarget_x)),
                max(0, min(source_y - target_y, focal_point_y - halftarget_y)),
            ]
            box.append(min(source_x, int(box[0]) + target_x))
            box.append(min(source_y, int(box[1]) + target_y))
            # See if the image should be "smart cropped".
            if smart_crop:
                left = top = 0
                right, bottom = source_x, source_y
                while diff_x:
                    slice = min(diff_x, max(diff_x // 5, 10))
                    start = im.crop((left, 0, left + slice, source_y))
                    end = im.crop((right - slice, 0, right, source_y))
                    add, remove = _compare_entropy(start, end, slice, diff_x)
                    left += add
                    right -= remove
                    diff_x = diff_x - add - remove
                while diff_y:
                    slice = min(diff_y, max(diff_y // 5, 10))
                    start = im.crop((0, top, source_x, top + slice))
                    end = im.crop((0, bottom - slice, source_x, bottom))
                    add, remove = _compare_entropy(start, end, slice, diff_y)
                    top += add
                    bottom -= remove
                    diff_y = diff_y - add - remove
                box = (left, top, right, bottom)
            # Finally, crop the image!
            im = im.crop(box)
    return im


def filters(im, detail=False, sharpen=False, **kwargs):
    """
    Pass the source image through post-processing filters.

    sharpen
        Sharpen the thumbnail image (using the PIL sharpen filter)

    detail
        Add detail to the image, like a mild *sharpen* (using the PIL
        ``detail`` filter).

    """
    if detail:
        im = im.filter(ImageFilter.DETAIL)
    if sharpen:
        im = im.filter(ImageFilter.SHARPEN)
    return im


def background(im, fit=None, background=None, crop=None, replace_alpha=None,
               **kwargs):
    """
    Add borders of a certain color to make the resized image fit exactly within
    the dimensions given.

    background
        Background color to use
    """
    if not fit:
        return im
    if not background:
        # Primary option not given, nothing to do.
        return im
    if not fit[0] or not fit[1]:
        # One of the dimensions aren't specified, can't do anything.
        return im
    x, y = im.size
    if x >= fit[0] and y >= fit[1]:
        # The image is already equal to (or larger than) the expected size, so
        # there's nothing to do.
        return im
    im = colorspace(im, replace_alpha=background, **kwargs)
    new_im = Image.new('RGB', fit, background)
    if new_im.mode != im.mode:
        new_im = new_im.convert(im.mode)
    offset = (fit[0]-x)//2, (fit[1]-y)//2
    new_im.paste(im, offset)
    return new_im
