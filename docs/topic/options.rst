=============
Image options
=============

The available image options will depend on the Easy Images engine being used.

The following options are all defined in the default PIL engine, separated out
into logical "processors" that can be customized or extended by
:ref:`subclassing the engine <customize-engine>`.

Resizing the image
==================

.. autofunction:: easy_images.engine.pil.processors.resize

White-space removal
-------------------

.. autofunction:: easy_images.engine.pil.processors.autocrop

Fill background when fitting
----------------------------

.. autofunction:: easy_images.engine.pil.processors.background


Modify the image
================

.. autofunction:: easy_images.engine.pil.processors.colorspace

.. autofunction:: easy_images.engine.pil.processors.filters
