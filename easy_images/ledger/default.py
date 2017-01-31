from easy_images.conf import settings
from django.utils.module_loading import import_string

default_ledger = import_string(settings.EASY_IMAGES__LEDGER)()  # noqa
