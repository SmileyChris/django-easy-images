from .app_settings import AppSettings


class Settings(AppSettings):
    """
    These default settings for easy-images can be specified in your Django
    project's settings to alter the behaviour of easy-images.

    Settings may be specified on the project as part of an ``EASY_IMAGES``
    dictionary (minus the ``'EASY_IMAGES__'`` prefix).
    """

    EASY_IMAGES__STORAGE = None
    """
    The default Django storage when saving processed images. If set to
    ``None``, uses default media storage.
    """

    EASY_IMAGES__LEDGER = 'easy_images.ledger.easy_images_db.DBLedger'
    # EASY_IMAGES__LEDGER = 'easy_images.ledger.easy_images_db.CachedDBLedger'

    EASY_IMAGES__ENGINE = 'easy_images.engine.pil.Engine'

    EASY_IMAGES__ALIASES = None
    """
    A dictionary of predefined alias options for different targets. See the
    :ref:`usage documentation <thumbnail-aliases>` for details.
    """

    # EASY_IMAGES__PROGRESSIVE = 100
    # """
    # Use progressive JPGs for thumbnails where either dimension is at least this
    # many pixels.

    # For example, a 90x90 image will be saved as a baseline JPG while a 728x90
    # image will be saved as a progressive JPG.

    # Set to ``False`` to never use progressive encoding.
    # """

    # EASY_IMAGES__PRESERVE_EXTENSION = None
    # """
    # To preserve specific extensions, for instance if you always want to create
    # lossless PNG thumbnails from PNG sources, you can specify these extensions
    # using this setting, for example::

    #     'PRESERVE_EXTENSION': ('png',)

    # All extensions should be lowercase.

    # Instead of a tuple, you can also set this to ``True`` in order to always
    # preserve the original extension.
    # """
    # EASY_IMAGES__PRESERVE_TRANSPARENCY = None
    # """
    # The type of image to save thumbnails with a transparency layer (e.g. GIFs
    # or transparent PNGs). For example::

    #     'PRESERVE_TRANSPARENCY': 'png',

    # If this setting is used, the filename can not be reliably assumed (like the
    # ``image_url`` filter does) since the extension can differ depending on
    # whether the source image contains a transparency layer.

    # Instead of a string containing the type, you can also set this to ``True``
    # in order to the original image format if there is a transparency layer.
    # """

    # EASY_IMAGES__RETINA_FILENAME = None
    # """
    # When thumbnailing, generates a higher resolution image for retina displays
    # using this filename. For example::

    #     'FILENAME': '{src_dir}{hash}{ext}',
    #     'RETINA_FILENAME': '{src_dir}{hash}_2x{ext}',

    # Creates a version of the thumbnails in high resolution that can be used by
    # a javascript layer to display higher quality thumbnails for high DPI
    # displays.

    # Generate a retina image by using the ``RETINA`` thumbnail option::

    #     opts = {'crop': (100, 100), 'RETINA': True}
    #     only_basic = EasyImage(obj.image, opts)

    # In a template tag, just the option name to enable it::

    #     {% image obj.image crop=50x50 RETINA %}  {# force hires #}

    # Apple Inc., formerly suggested to use ``@2x`` as infix, but later changed
    # their mind and now suggests to use ``_2x``, since this is more portable.
    # """
