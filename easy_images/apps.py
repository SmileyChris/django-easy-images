from django.apps import AppConfig, apps
from django.db.models import FileField


class EasyImagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "easy_images"

    def ready(self):
        from django.db.models.signals import post_save, pre_save

        from easy_images.models import EasyImage
        from easy_images.signals import (
            find_uncommitted_filefields,
            signal_committed_filefields,
        )

        # Only connect the signals to (non-EasyImage) models that have FileFields.
        for model in apps.get_models():
            if issubclass(model, EasyImage):
                continue
            if not any(isinstance(f, FileField) for f in model._meta.get_fields()):
                continue
            pre_save.connect(find_uncommitted_filefields, sender=model)
            post_save.connect(signal_committed_filefields, sender=model)
