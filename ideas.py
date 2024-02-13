from __future__ import annotations

import abc
import json
import mimetypes
import re
from abc import ABC
from dataclasses import dataclass
from hashlib import shake_128
from typing import TypedDict
from uuid import UUID

from django.core.files.storage import storages
from django.db import models
from django.db.models import FieldFile
from django.utils.text import smart_split


class OptionError(Exception):
    pass


class Option:
    def __init__(self, key: str | None = None):
        if not key:
            key = self.get_key()
        assert key
        self.key = key

    def get_key(self):
        name = self.__class__.__name__
        if name.endswith("Option"):
            return name[:-6]
        return name.lower()

    def get_value(self, value: str):
        return value


class BooleanOption(Option):
    def get_value(self, value: str):
        if value.lower() in ("false", "no", "off", "0"):
            return False
        if value.lower() in ("", "true", "yes", "on", "1"):
            return True
        raise OptionError(f"Invalid value for {self.get_key()}: {value}")


class SizeOption(Option):
    def get_value(self, value: str):
        match = re.match(r"^(\d+)[,x](\d)$", value, re.IGNORECASE)
        if not match:
            raise OptionError(f"Invalid value for {self.get_key()}: {value}")
        return (int(match.group(1)), int(match.group(2)))


class SourceOptions(TypedDict):
    storage: str
    name: str
    format: str
    width: int
    height: int


class State(TypedDict):
    img: FieldFile | None
    opts: SourceOptions


class CheckState(TypedDict):
    source: State
    current_opts: SourceOptions


class RunState(TypedDict):
    source: State
    current: State


class Filter(ABC):
    options: list[Option] = []
    requires_path = False
    requires_source_to_check = True

    @abc.abstractmethod
    def check(self, state: CheckState, options: dict) -> bool | SourceOptions:
        raise NotImplementedError

    @abc.abstractmethod
    def run(self, img, options: dict):
        raise NotImplementedError


class OptimizeFilter(Filter):
    options = [BooleanOption("optimize")]
    requires_path = False
    requires_source_to_check = False

    def check(self, state: State, options: dict) -> bool:
        return options.get("optimize", False)

    def run(self, img, options: dict):
        return options


def pick_image_storage(instance, filename):
    check_storages = ["image"]
    if instance.storage:
        if image_storage_name := (
            instance.storage.opts.get("image_storage_name")
            if isinstance(instance.storage.opts, dict)
            else None
        ):
            if image_storage_name not in check_storages:
                check_storages.insert(0, image_storage_name)
    for storage_name in check_storages:
        if storage_name in storages:
            return storages[storage_name]
    return storages["default"]


class SourceManager(models.Manager):
    def hash_from_file(self, *, file: FieldFile, options: dict[str, str]) -> UUID:
        storage = file.storage.name
        name = file.name
        return self.hash(name=name, storage=storage, options=options)

    def hash(self, *, name: str, storage: str, options: dict[str, str]) -> UUID:
        opts = json.dumps(options, sort_keys=True)
        # Create a hash of the storage, name, and options.
        hash = shake_128(data=f"{storage}:{name}:{opts}".encode("utf-8"))
        return UUID(bytes=hash.digest(32))

    def from_file(
        self, file: FieldFile, options: dict[str, str]
    ) -> PictureSource | None:
        pk = self.hash_from_file(file=file, options=options)
        try:
            return self.get(pk=pk)
        except self.model.DoesNotExist:
            return None


class PictureSource(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    complete = models.BooleanField(default=None, null=True)
    storage = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    mimetype = models.CharField(max_length=128)
    opts = models.JSONField()
    img = models.ImageField(
        storage=pick_image_storage,
        height_field="height",
        width_field="width",
        blank=True,
    )
    height = models.IntegerField(null=True)
    width = models.IntegerField(null=True)

    objects = SourceManager()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = PictureSource.objects.hash(self.img, self.opts)
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["storage", "name"]),
        ]


PICTURE_SOURCES = {
    "thumb": "size=100x100 crop PROCESS",  # Processed inline whenever this source is requested
    "big_thumb": "size=200x200 crop",  # Queued for processing whenever this source is requested
    "BASE": "optimize size=1024x768 QUEUE PROCESS:thumb QUEUE:big_thumb",  # Queued for processing whenever a new image is saved, when this is processed it will also process thumb and queue big_thumb
    "BASE:webp": "size=1920x1080 PROCESS QUEUE:thumb QUEUE:big_thumb",  # Processed whenever a new image is saved, and queue thumb and big_thumb
}

"""
{{ report.image|picture:"square_thumb" }}
{% image report.image 100x100 optimize %}

{% picture report.image alt="Description of the image" %}
   {% source "thumb" "big_thumb 2x" media="(max-width: 600px)" %}
{% endpicture %}

make_pictures(["thumb 500w"])

generator = Generator(
    sources=[
        Source("thumb", "big_thumb 2x", media="(max-width: 600px)")
    ],
    media="(max-width: 600px)"
)
for report in reports.all():
    generator(report.image)
generator.html(report.image)  # html of one picture tag. For example:
# <picture>
#   <source srcset="thumb.jpg, big_thumb.jpg 2x" media="(max-width: 600px)">
#   <source srcset="base-processed.jpg" type="image/jpeg" height="800" width="600">
#   <img src="base.jpg" alt="Description of the image">
# </picture>
generator.get(report.image)   # dict of one picture. For example:
# {
#   "src": "base.jpg",
#   "alt": "Description of the image",
#   "sources": [
#      {"srcset": "thumb.jpg, big_thumb.jpg 2x", "type": "image/jpeg", "media": "(max-width: 600px)"}
#      {"srcset": "base-processed.jpg", "type": "image/jpeg", "height": 800, "width": 600}
#   ],
# }
generator.all()               # a list of all the pictures (in dict form)


Fallback options if not generated yet:
 - source url (with checked option size if possible)
 - placeholder image


Batch lookup / generate for efficiency?

ImageQueue for processing images

"""


@dataclass(frozen=True)
class ParsedOptions:
    options: dict[str, str]
    meta: dict[str, str | None]


def parse_options_string(options_string: str) -> ParsedOptions:
    options: dict[str, str] = {}
    meta: dict[str, str | None] = {}
    for part in smart_split(options_string):
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            meta_key, meta_value = (key, None) if ":" not in key else key.split(":", 1)
            if meta_key == meta_key.upper():
                meta[meta_key] = meta_value
                continue
            key, value = part, ""
            options[key] = value
    return ParsedOptions(options, meta)


def get_options_from_alias(
    alias: str, filename: str | None = None
) -> ParsedOptions | None:
    aliases = [alias]
    # Guess the file type based on the filename
    if filename:
        if mimetype := mimetypes.guess_type(filename)[0]:
            if "/" in mimetype:
                primary, secondary = mimetype.split("/", 1)
                if primary == "image":
                    aliases.insert(0, f"{alias}:{secondary}")
    for alias in aliases:
        if alias in PICTURE_SOURCES:
            return PICTURE_SOURCES[alias]
    return


class QueuedImage(TypedDict):
    file: FieldFile
    height: int
    width: int


def get_image(file: FieldFile, options) -> ProcessedLedger:
    ledger
