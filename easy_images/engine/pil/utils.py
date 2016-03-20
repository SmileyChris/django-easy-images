import math
import os
try:
    from cStringIO import cStringIO as BytesIO
except ImportError:
    from django.utils.six import BytesIO

from PIL import Image


def image_entropy(im):
    """
    Calculate the entropy of an image. Used for "smart cropping".
    """
    hist = im.histogram()
    hist_size = float(sum(hist))
    hist = [h / hist_size for h in hist]
    return -sum([p * math.log(p, 2) for p in hist if p != 0])


def is_transparent(image):
    """
    Check to see if an image is transparent.
    """
    return (image.mode in ('RGBA', 'LA') or
            (image.mode == 'P' and 'transparency' in image.info))


def get_exif_orientation(im):
    """
    Return the image's EXIF orientation data.
    """
    try:
        exif = im._getexif()
        return int(exif.get(0x0112))
    except Exception:
        # There are many ways that _getexif fails, we're just going to blanket
        # cover them all.
        return None


def exif_orientation(im):
    """
    Rotate and/or flip an image to respect the image's EXIF orientation data.
    """
    orientation = get_exif_orientation(im)

    if orientation in (2, 4, 5, 7):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)

    if orientation in (7, 8):
        im = im.transpose(Image.ROTATE_90)
    elif orientation in (3, 4):
        im = im.transpose(Image.ROTATE_180)
    elif orientation in (5, 6):
        im = im.transpose(Image.ROTATE_270)

    return im


def save(filename, im, options, destination=None):
    pil_options = options.copy()
    if destination is None:
        destination = BytesIO()
    # Ensure plugins are fully loaded so that Image.EXTENSION is populated.
    Image.init()
    fmt = Image.EXTENSION.get(
        os.path.splitext(filename)[1].lower(), 'JPEG')
    if fmt in ('JPEG', 'WEBP'):
        pil_options.setdefault('quality', 85)
    saved = False
    if fmt == 'JPEG':
        progressive = pil_options.pop('progressive', 100)
        if progressive:
            if progressive is True or max(im.size) >= int(progressive):
                pil_options['progressive'] = True
        try:
            im.save(destination, format=fmt, optimize=1, **pil_options)
            saved = True
        except IOError:
            # Try again, without optimization (PIL can't optimize an image
            # larger than ImageFile.MAXBLOCK, which is 64k by default).
            # This shouldn't be triggered very often these days, as recent
            # versions of pillow avoid the MAXBLOCK limitation.
            pass
    if not saved:
        im.save(destination, format=fmt, **pil_options)
    if hasattr(destination, 'seek'):
        destination.seek(0)
    return destination
