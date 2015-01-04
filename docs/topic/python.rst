=====================
Easy Images in Python
=====================

The primary way of interacting with the Easy Images components is with the
:cls:`~easy_images.image.EasyImage` class.

Create an instance of this class by providing a source image and generation
options.


Basic usage
===========

The source image can be defined as a text path (relative to the root of the
default storage engine) or a Django ``File`` class with a name defined.
The generation options allow for manipulation of the source image, for example
proportionally resizing the image to fit inside a bounding box::

    >>> from easy_images.image import EasyImage
    >>> img = EasyImage('people/chris.jpg', {'fit': (128, 128)})

Creating an ``EasyImage`` instance does not trigger any complex behaviour.
The default behaviour when calling the ``url`` property (which is also the
default text representation of the instance) will check if the image is
generated, otherwise it will be generated and saved first::

    >>> str(img)   # this will generate the image if not found
    /media/people/x1QrogNLDSlzMEFx9I9cYx9IOkk.jpg

Explicitly check whether the image exists like so::

    >>> img.exists
    True

More functionality
------------------

Some other useful properties are found on ``.meta``.

Check the :cls:`easy_images.image.EasyImage` class for reference documentation
on all properties and methods this class provides.

Batch loading
=============

Some backends are able to more efficiently load multiple images in a single
batch.

    >>> from easy_images.image import EasyImageBatch
    >>> batch = EasyImageBatch()
    >>> batch.add('people/chris.jpg', {'fit': (128, 128)})
    >>> batch.add('people/chris.jpg', {'crop': (64, 64), 'upscale': True})
    >>> for easy_image in batch:
    ...     print(easy_image.url)

The ``EasyImageBatch`` can be instanciated with a list of source & options
tuple pairs rather than adding them individually via the ``source`` parameter.

You can also specify ``engine`` and/or ``ledger`` parameters to use an
alternative to the defaults.

Annotating a list or queryset
-----------------------------

Use the ``annotate`` shortcut as an easy way of annotating a list of objects
with ``EasyImage`` objects (all loaded in a single batch).

Apart from the list of objects, the shortcut needs a map of options that define
the options for each ``EasyImage`` - a dictonary where each key is the
attribute name to annotate the object with, each value being an ``EasyImages``
options dictionary. If using aliases, you can use the
:meth:`~easy_images.aliases.Library.map` method to build this::

    >>> from easy_images.aliases import aliases
    >>> opts_map = aliases.map('square', 'large', 'fullscreen')

The source can be given as a string (which will be looked up as an attribute of
each object) or a callable that accepts the object and returns the source.

For example::

    >>> from easy_images.image import annotate
    >>> annotate(some_queryset, opts_map, 'person')
