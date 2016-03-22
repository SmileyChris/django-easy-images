========================
Easy Images in Templates
========================

Access easy-images in the template layer is... easy.

You can use (or extend) an alias, or just specify the options all directly in
your template using ``{% image %}`` template tag.

You will have to load the easy_images template tag library into your template
like so::

    {% load easy_images %}


``image`` Template Tag
======================

You can output the URL for an image while specifying the options in the
template with the ``{% image %}`` tag. The first argument should be the source
image (or an EasyImage), all other arguments are turned into options::

    {% image person.photo crop=32,32 upscale %}

Use ``as name`` at the end of the tag to save the ``EasyImage`` instance to
the context rather than just outputting the URL::

    {% image person.photo crop=32,32 as thumb %}
    Thumbnail name is: {{ thumb.name }}
    {% if not thumb.exists %}Thumbnail has not yet been generated!{% endif %}

Use ``alias 'some-alias'`` within the tag to pull initial options from an
image alias::

    {% image person.avatar alias 'icon' %}
    {% image person.avatar alias 'headshot' target=person.avatar_focal_point %}

Batch processing
----------------

To batch process a bunch of image tags, simply place a single
``{% imagebatch %}`` tag before any images::

    {% imagebatch %}

    {% for person in people %}
        <div>
            {% image person.avatar alias 'square' as avatar %}
            <img src="{{ avatar }}" alt="">
            {{ person }}
        </div>
    {% endfor %}

The template code after the ``imagebatch`` is virtually rendered before its
real render, which gathers the image options and then retrieves or generates
them all in one batch.


Examples
========

Provide separate images for multiple pixel densities::

    {% image person.photo fit=800,600 as person_photo %}
    <img
      src="{{ person_photo }}"
      srcset="{% image person_photo HIGHRES=1.5 %} 1.5x,
              {% image person_photo HIGHRES=2 %} 2x"
      alt="">
