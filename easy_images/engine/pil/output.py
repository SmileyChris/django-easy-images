import os
try:
    from cStringIO import cStringIO as BytesIO
except ImportError:
    from django.utils.six import BytesIO

from PIL import Image

from . import utils


class PILOutput(object):

    def write_image(self, image, filename, destination=None, **options):
        """
        Save a PIL image.
        """
        if destination is None:
            destination = BytesIO()
        # Ensure plugins are fully loaded so that Image.EXTENSION is populated.
        Image.init()
        fmt = Image.EXTENSION.get(
            os.path.splitext(filename)[1].lower(), 'JPEG')
        if fmt in ('JPEG', 'WEBP'):
            options.setdefault('quality', 85)
        saved = False
        if fmt == 'JPEG':
            progressive = options.pop('progressive', 100)
            if progressive:
                if progressive is True or max(image.size) >= int(progressive):
                    options['progressive'] = True
            try:
                image.save(destination, format=fmt, optimize=1, **options)
                saved = True
            except IOError:
                # Try again, without optimization (PIL can't optimize an image
                # larger than ImageFile.MAXBLOCK, which is 64k by default).
                # This shouldn't be triggered very often these days, as recent
                # versions of pillow avoid the MAXBLOCK limitation.
                pass
        if not saved:
            image.save(destination, format=fmt, **options)
        if hasattr(destination, 'seek'):
            destination.seek(0)
        return destination

    def build_meta(self, image):
        """
        Build a dictionary of metadata for an image.
        """
        return {
            'size': image.size,
            'transparent': utils.is_transparent(image),
        }
