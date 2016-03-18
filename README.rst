Easy Images
===========

Easy images for Django.

Processes a source image via a dictionary of options. For example, the
following dictionary would resize the source image down and crop it to output
a 64x64 image::

    {'crop': (64, 64)}


Usage with Aliases
------------------

To make it easier to manage the different option dictionaries, it is
recommended to define aliases that you can use to centralize all the image
generation options in a single place.

In your settings::

    EASY_IMAGES = {
        'ALIASES': {
            'smallbox': {'crop': (32, 32), 'upscale': True},
        },
    }

Then to generate thumbs in a Django template just use::

    <img src="{{ person.avatar|image:'smallbox' }}" alt="">

Or in Python, use::

    from easy_images.aliases import aliases
    from easy_images.images import EasyImage
    EasyImage('some/file', aliases.get('smallbox')).generate()


See docs for details.