from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING, NamedTuple, cast

from django.db.models import F, FileField, ImageField, Model
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from django.utils.html import escape
from typing_extensions import Unpack

from easy_images.options import ParsedOptions
from easy_images.signals import file_post_save, queued_img
from easy_images.types import BuildChoices, ImgOptions, Options

if TYPE_CHECKING:
    from easy_images.models import EasyImage


format_map = {"avif": "image/avif", "webp": "image/webp"}


option_defaults: ImgOptions = {
    "quality": 80,
    "ratio": "video",
    "crop": True,
    "densities": [2],
    "format": "avif",
}


class Img:
    def __init__(self, **options: Unpack[ImgOptions]):
        all_options = option_defaults.copy()
        all_options.update(options)
        self.options = all_options

    def extend(self, **options: Unpack[ImgOptions]) -> Img:
        new_options = self.options.copy()
        if (
            "base" in self.options
            and self.options["base"]
            and "base" in options
            and options["base"] is not None
        ):
            new_base = self.options["base"].copy()
            new_base.update(options["base"])
            options["base"] = new_base
        new_options.update(options)
        return Img(**new_options)

    def __call__(
        self,
        source: FieldFile,
        alt: str | None = None,
        build: BuildChoices = None,
        send_signal=True,
    ):
        return BoundImg(source, alt=alt, img=self, build=build, send_signal=send_signal)

    def queue(
        self,
        model: type[Model],
        *,
        fields: type[FileField] | list[str] | None = ImageField,
        build: BuildChoices = None,
    ):
        """
        Listen for saves to files on a specific model.

        By default, this will listen for saves to any ImageField on the model.
        """

        def handle_file(fieldfile: FieldFile, **kwargs):
            if fields:
                if isinstance(fields, list):
                    if fieldfile.field.name not in fields:
                        return
                elif not isinstance(fieldfile, fields):
                    return
            self(fieldfile, build=build, send_signal=False)

        file_post_save.connect(handle_file, sender=model, weak=False)


class SrcSetItem(NamedTuple):
    thumb: EasyImage
    options: Options


class BoundImg:
    alt: str
    base: EasyImage | None
    srcset: list[SrcSetItem]

    def __init__(
        self,
        file: FieldFile,
        *,
        alt: str | None,
        img: Img,
        build: BuildChoices = None,
        send_signal: bool,
    ):
        from . import engine
        from .models import EasyImage, ImageStatus

        self.file = file
        self.img = img

        queued = False
        if "width" in img.options and img.options["width"] is not None:
            base_options = ParsedOptions(file.instance, **img.options)
            base_options.mimetype = "image/jpeg"
            self.base, created = EasyImage.objects.from_file(file, base_options)
            if created and not build:
                queued = True
            base_width = base_options.width
        else:
            self.base = None
            base_width = None

        densities = img.options.get("densities") or []

        options = cast(Options, img.options.copy())
        if "format" in img.options and img.options["format"]:
            options["mimetype"] = format_map[img.options["format"]]
            if 1 not in densities and options["mimetype"] != "image/jpeg":
                densities.insert(0, 1)
        else:
            source_type = mimetypes.guess_type(file.name)[0]
            options["mimetype"] = source_type or "image/jpeg"

        srcset: list[SrcSetItem] = []
        sizes_attr: list[str] = []

        sizes = img.options.get("sizes")
        max_width = base_width
        if sizes and max_width:
            img_options = cast(Options, options).copy()
            img_options["srcset_width"] = max_width
            max_options = img_options
            for media, size in sizes.items():
                media_options = options.copy()
                if isinstance(size, dict):
                    media_options.update(size)
                else:
                    media_options["width"] = size
                parsed_options = ParsedOptions(file.instance, **media_options)
                if not parsed_options.width:
                    raise ValueError("Size options must have a width")
                media_options["srcset_width"] = parsed_options.width
                if isinstance(media, int):
                    media = f"(max-width: {media}px)"
                if parsed_options.width > max_width and "print" not in media:
                    max_options = media_options
                    max_width = max_width
                sizes_attr.append(f"{media} {parsed_options.width}px")
                instance, created = EasyImage.objects.from_file(
                    file, ParsedOptions(file.instance, **media_options)
                )

                srcset.append(SrcSetItem(instance, media_options))
                if created and build != "srcset":
                    queued = True
            instance, created = EasyImage.objects.from_file(
                file, ParsedOptions(file.instance, **img_options)
            )
            srcset.append(SrcSetItem(instance, img_options))
            if created and build != "srcset":
                queued = True
            sizes_attr.append(f"{max_width}px")
            max_density = max(densities) if densities else 1
            if max_density > 1:
                # Find the max size and multiply it by the max density to get an extra size that should be generated.
                high_density_options = max_options.copy()
                high_density_options["width_multiplier"] = max_density
                instance, created = EasyImage.objects.from_file(
                    file, ParsedOptions(file.instance, **high_density_options)
                )
                srcset.append(SrcSetItem(instance, high_density_options))
                if created and build != "srcset":
                    queued = True
        elif densities:
            for density in densities:
                alt_options = options.copy()
                alt_options["width_multiplier"] = density
                instance, created = EasyImage.objects.from_file(
                    file, ParsedOptions(file.instance, **alt_options)
                )
                srcset.append(SrcSetItem(instance, alt_options))
                if created and build != "srcset":
                    queued = True

        if build:
            build_options: list[tuple[EasyImage, ParsedOptions]] = []
            if build == "srcset":
                for srcset_item in srcset:
                    if srcset_item.thumb.image:
                        continue
                    build_options.append(
                        (
                            srcset_item.thumb,
                            ParsedOptions(file.instance, **srcset_item.options),
                        )
                    )
            if self.base:
                build_options.append((self.base, base_options))
            if build_options:
                try:
                    source_img = engine.efficient_load(
                        file=self.file,
                        options=[opts[1] for opts in build_options],
                    )
                except Exception:
                    for im, opts in build_options:
                        EasyImage.objects.filter(
                            pk=im.pk, status_changed_date=im.status_changed_date
                        ).update(
                            error_count=F("error_count") + 1,
                            status=ImageStatus.SOURCE_ERROR,
                            status_changed_date=timezone.now(),
                        )
                else:
                    for im, opts in build_options:
                        im.build(
                            source_img=source_img,
                            options=opts,
                        )

        if all(srcset_item.thumb.image for srcset_item in srcset):
            self.srcset = srcset
        elif srcset:
            self.srcset = []
        self.sizes = ", ".join(sizes_attr)

        if isinstance(alt, str):
            self.alt = alt
        elif "alt" in img.options and isinstance(img.options["alt"], str):
            self.alt = img.options["alt"]
        else:
            self.alt = ""

        if queued and send_signal:
            queued_img.send(sender=img, instance=file)

    def as_html(self):
        srcset = []
        for srcset_item in self.srcset:
            srcset_str = srcset_item.thumb.image.url
            if w := srcset_item.options.get("srcset_width"):
                if mult := srcset_item.options.get("width_multiplier"):
                    w *= mult
                srcset_str += f" {w}w"
            elif w := srcset_item.options.get("width_multiplier"):
                if w != 1:
                    srcset_str += f" {w:g}x"
            srcset.append(srcset_str)
        img_attrs = self.img.options.get("img_attrs")
        if img_attrs:
            img_attrs = img_attrs.copy()
        else:
            img_attrs = {}

        img_attrs["src"] = self.base_url()

        if srcset:
            img_attrs["srcset"] = ", ".join(srcset)
            if self.sizes:
                img_attrs["sizes"] = self.sizes

        img_attrs["alt"] = self.alt

        attrs = " ".join(
            (f'{k}="{escape(v)}"' if v is not True else k) for k, v in img_attrs.items()
        )
        return f"<img {attrs}>"

    def base_url(self):
        return self.base.image.url if self.base and self.base.image else self.file.url
