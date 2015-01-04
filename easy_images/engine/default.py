from easy_images.conf import settings
try:
    from django.utils.module_loading import import_string
except ImportError:   # pragma: no cover  (Django <1.7)
    from django.utils.module_loading import import_by_path as import_string

# Set the default engine.
default_engine = import_string(settings.EASY_IMAGES__ENGINE)()  # noqa

# Set the default storage.
storage_setting = settings.EASY_IMAGES__STORAGE
if storage_setting:
    default_storage = import_string(storage_setting)()
else:
    from django.core.files.storage import default_storage  # noqa
