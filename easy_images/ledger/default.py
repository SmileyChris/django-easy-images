from easy_images.conf import settings
try:
    from django.utils.module_loading import import_string
except ImportError:   # pragma: no cover  (Django <1.7)
    from django.utils.module_loading import import_by_path as import_string

default_ledger = import_string(settings.EASY_IMAGES__LEDGER)()  # noqa
