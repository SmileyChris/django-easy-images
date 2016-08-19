import re

from django.utils import six


def colorspace(im, bw=False, replace_alpha=False, **kwargs):
    """
    Convert images to the correct color space.

    A passive option (i.e. always processed) of this function is the image
    (unless grayscale) is converted to RGB colorspace.

    This processor should be listed before :func:`resize` so palette is changed
    before the image is resized.

    bw
        Make the image grayscale (not really just black & white).

    replace_alpha
        Replace any transparency layer with a solid color. For example,
        ``replace_alpha='#fff'`` would replace the transparency layer with
        white.

    """
    is_grayscale = im.mode in ('L', 'LA')
    new_mode = im.mode
    if is_grayscale or bw:
        new_mode = 'L'
    else:
        new_mode = 'RGB'

    if im.transparent:
        if replace_alpha:
            im = im.replace_alpha(color=replace_alpha)
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
        return im.filter([('autocrop', True)])
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
        size.

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
        ``40`` will clip 20% off each side of the source image before resizing.

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
        im = im.resize(
            (int(round(source_x * scale)), int(round(source_y * scale))),
            antialias=True)

    if crop:
        # Use integer values now.
        source_x, source_y = im.size
        # Difference between new image size and requested size.
        diff_x = int(source_x - min(source_x, target_x))
        diff_y = int(source_y - min(source_y, target_y))
        cropped_image = smart_crop and im.smart_crop((target_x, target_y))
        if cropped_image and cropped_image is not im:
            im = cropped_image
        elif diff_x or diff_y:
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
            # Finally, crop the image!
            im = im.crop(box)
    return im


def filters(im, detail=False, sharpen=False, **kwargs):
    """
    Pass the source image through post-processing filters.

    sharpen
        Sharpen the image.

    detail
        Add detail to the image -- like a mild *sharpen*.

    """
    filters = []
    if detail:
        filters.append(('detail', True))
    if sharpen:
        filters.append(('sharpen', True))
    return im


def background(im, fit=None, background=None, **kwargs):
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
    if not im.transparent:
        im = im.convert(im.mode + 'A')
    im = im.canvas(fit)
    return im.replace_alpha(background)
