========================
Easy Images in Templates
========================

There are a few ways to access easy-images in the template layer.

If you have predefined aliases (recommended), the simplest is to use the
``image`` filter passing it the alias.

If you want to extend options provided in an alias, or just specify the options
all directly in your template then use the ``{% image %}`` template tag.

To use either the filter or template tag, you will have to load the easy_images
template tag library into your template like so::

    {% load easy_images %}


``image`` Filter
================

To output the URL for an aliased image, use the filter like so:

.. code-block:: html

    <img src="{{ person.avatar|image:'thumbnail' }}" alt="">

The output from the filter is actually an :cls:`~easy_images.core.EasyImage`
class, so if you would like to access other information then just use Django's
standard ``{% with %}`` tag:

.. code-block:: html

    {% with thumb=person.photo|image:'thumbnail' %}
    <img src="{{ thumb }}" alt=""
         width="{{ thumb.width }}" height="{{ thumb.height }}">
    {% endwith %}

Application-specific aliases
----------------------------

If you have aliases that are limited to an application, you must get the
thumbnail options using the following template tag, rather than just as a
string on the ``image`` filter:

.. code-block:: html

    {% image_alias 'thumbnail' as thumbnail_opts %}
    <img src="{{ person.avatar|image:thumbnail_opts }}" alt="">


``image`` Template Tag
======================

You can output the URL for an image while specifying the options in the
template with the ``{% image %}`` tag. The first argument should be the source
image, all other arguments are turned into options::

    {% image person.photo crop=32,32 upscale %}

Use ``as name`` at the end of the tag to save the ``EasyImage`` instance to the
context rather than just outputting the URL::

    {% image person.photo crop=32,32 as thumb %}
    Thumbnail name is: {{ thumb.name }}
    {% if not thumb.exists %}Thumbnail has not yet been generated!{% endif %}

You can use this tag to extend the options of an existing EasyImage, generating
a new image::

    {% with headshot=person.avatar|image:'headshot' %}
        {% image headshot target=person.headshot_focal_point %}
    {% endwith %}
