=======================
Customizing Easy Images
=======================

Three main areas to customize::

Custom settings
===============

.. autoclass:: easy_images.conf.settings.Settings
    :members:

Custom ledger
=============

Ensure your ledger extends ``BaseLedger``. Look at source for the current
implementations of ledgers for some inspiration.

.. autoclass:: easy_images.ledger.base.BaseLedger
    :members:

Custom engine
=============

Like with custom ledgers, ensure your engine extends ``BaseEngine``::

.. autoclass:: easy_images.engine.base.BaseEngine
    :members:
