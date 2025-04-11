from __future__ import annotations

from typing import cast
from uuid import UUID

import django_stubs_ext
from django.core.files.storage import (
    Storage,
    storages,  # type: ignore (storages isn't in the stubs)
)
from django.core.files.storage.handler import InvalidStorageError
from django.db import models
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from easy_images import engine
from easy_images.options import ParsedOptions

django_stubs_ext.monkeypatch()


def pick_image_storage() -> Storage:
    try:
        return storages["easy_images"]
    except InvalidStorageError:
        return storages["default"]


def image_name_and_storage(file: FieldFile) -> tuple[str, str]:
    return file.name, get_storage_name(file.storage)


def get_storage_name(storage: Storage) -> str:
    for name in storages.backends:
        if storage == storages[name]:
            return name
    raise ValueError(f"Unknown storage: {storages}")


class EasyImageManager(models.Manager["EasyImage"]):
    def hash(self, *, name: str, storage: str, options: ParsedOptions) -> UUID:
        hash = options.hash()
        hash.update(f":{storage}:{name}".encode())
        return UUID(bytes=hash.digest()[:16])

    def from_file(self, file: FieldFile, options: ParsedOptions):
        name, storage = image_name_and_storage(file)
        pk = self.hash(name=name, storage=storage, options=options)
        return self.get_or_create(
            pk=pk,
            defaults=dict(
                storage=storage,
                name=name,
                args=options.to_dict(),
            ),
        )

    def all_for_file(self, file: FieldFile):
        name, storage = image_name_and_storage(file)
        return self.filter(name=name, storage=storage)


class ImageStatus(models.IntegerChoices):
    QUEUED = 0, _("Queued")
    BUILDING = 1, _("Building")
    BUILT = 2, _("Built")
    SOURCE_ERROR = 3, _("Source error")
    BUILD_ERROR = 4, _("Build error")


class EasyImage(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(choices=ImageStatus.choices, default=0)
    error_count = models.PositiveSmallIntegerField(default=0)
    status_changed_date = models.DateTimeField(null=True)
    storage = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    args = models.JSONField[dict[str, str]]()
    image = models.ImageField(
        storage=pick_image_storage,
        upload_to="img/thumbs",
        height_field="height",
        width_field="width",
        blank=True,
    )
    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)

    objects: EasyImageManager = EasyImageManager()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = EasyImage.objects.hash(
                name=self.name,
                storage=self.storage,
                options=ParsedOptions(**self.args),
            )
        super().save(*args, **kwargs)

    def build(
        self,
        source_img: engine.Image | None = None,
        options: ParsedOptions | None = None,
        force=False,
        raise_error=False,
    ):
        now = timezone.now()
        image_qs = EasyImage.objects.filter(pk=self.pk)
        if force:
            image_qs.update(status=ImageStatus.BUILDING, status_changed_date=now)
        elif self.image or not image_qs.exclude(
            models.Q(status=ImageStatus.BUILDING) | models.Q(status=ImageStatus.BUILT)
        ).update(status=ImageStatus.BUILDING, status_changed_date=now):
            # Already built (or being generated elsewhere).
            return False
        self.status = ImageStatus.BUILDING
        self.status_changed_date = now
        if not source_img:
            try:
                storage = storages[self.storage]
                file = storage.open(self.name)
                source_img = engine.efficient_load(file, options)
            except Exception:
                self.error_count += 1
                self.status = ImageStatus.SOURCE_ERROR
                self.status_changed_date = timezone.now()
                self.save()
                if raise_error:
                    raise
                return False
        try:
            if not options:
                options = ParsedOptions(**self.args)
            if size := options.size:
                img = engine.scale_image(
                    source_img,
                    size,
                    focal_window=options.window,
                    crop=options.crop,
                    contain=options.contain,
                )
            else:
                img = source_img
            self.height = img.height
            self.width = img.width
            extension = {
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
                "image/avif": ".avif",
            }.get(options.mimetype or "", ".jpg")
            file = engine.vips_to_django(
                img, f"{self.id.hex}{extension}", quality=options.quality
            )
        except Exception:
            self.error_count += 1
            self.status = ImageStatus.BUILD_ERROR
            self.status_changed_date = timezone.now()
            self.save()
            if raise_error:
                raise
            return False
        self.image = cast(
            ImageFieldFile,  # Avoid some typing issues
            file,
        )
        self.status = ImageStatus.BUILT
        self.status_changed_date = timezone.now()
        self.save()
        file.close()
        return True

    class Meta:
        indexes = [
            models.Index(
                fields=["storage", "name"], name="easy_images_storage_and_name"
            ),
        ]
