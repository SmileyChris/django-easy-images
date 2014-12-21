======================
Installing Easy Images
======================

Install from pip (from the root of this repository):

.. code-block:: console

    pip install .

Add application(s) to your Django settings module. For a standard setup, you'll
want:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'easy_images',
        'easy_images.ledger.easy_images_db',
    )


Queueing
========

To use the built-in basic database based queuing engine rather than real-time
generation, you'll want to add:

.. code-block:: python

    EASY_IMAGES = {
        'ENGINE': 'easy_images.engine.pil.DBQueueEngine'
    }

    INSTALLED_APPS = (
        ...
        'easy_images.engine.easy_images_db_queue',
    )

You'll also want to add this to your cron::

    ./manage.py generate_images --unless-lock=myproject_images
