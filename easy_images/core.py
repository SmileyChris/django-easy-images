from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING, NamedTuple, cast, get_args
from uuid import UUID

from django.db.models import F, FileField, ImageField, Model
from django.db.models.fields.files import FieldFile
from django.utils import timezone
from django.utils.html import escape
from typing_extensions import Unpack

from easy_images.options import ParsedOptions
from easy_images.signals import file_post_save, queued_img
from easy_images.types_ import (
    BuildChoices,
    ImgOptions,
    Options,
    WidthChoices,
)

if TYPE_CHECKING:
    from .models import EasyImage


format_map = {"avif": "image/avif", "webp": "image/webp", "jpeg": "image/jpeg"}

option_defaults: ImgOptions = {
    "quality": 80,
    "ratio": "video",
    "crop": True,
    "contain": True,
    "densities": [2],
    "format": "webp",
}


class Img:
    """Configuration object for generating images."""

    def __init__(self, **options: Unpack[ImgOptions]):
        all_options = option_defaults.copy()
        all_options.update(options)
        self.options = all_options

    def extend(self, **options: Unpack[ImgOptions]) -> Img:
        """Create a new Img instance with updated options."""
        new_options = self.options.copy()
        # Deep copy 'base' options if they exist in both current and new options
        if (
            "base" in self.options
            and self.options["base"]
            and "base" in options
            and options["base"] is not None
        ):
            new_base = self.options["base"].copy()
            new_base.update(options["base"])
            options["base"] = new_base  # Update the options dict that will be used
        new_options.update(options)
        return Img(**new_options)

    def __call__(
        self,
        source: FieldFile,
        alt: str | None = None,
        build: BuildChoices = None,
        send_signal=True,
    ) -> BoundImg:
        """Bind this image configuration to a specific source file."""
        return BoundImg(source, alt=alt, img=self, build=build, send_signal=send_signal)

    def queue(
        self,
        model: type[Model],
        *,
        fields: type[FileField] | list[str] | None = ImageField,
        build: BuildChoices = None,
        send_signal: bool = True,
        dispatch_uid: str | None = None,
    ):
        """
        Listen for saves to files on a specific model and bind this Img config.

        By default, this will listen for saves to any ImageField on the model.

        :param model: The model to listen for saves on.
        :param fields: The field type or specific field names to listen for saves on.
                       If None, listens for saves on any FieldFile.
                       Defaults to ImageField.
        :param build: The build option to use when building the image immediately after save.
        :param send_signal: Whether to send the queued_img signal if there are versions
                            of the image that need to be built.
        :param dispatch_uid: A unique ID for the signal receiver, used for disconnecting.
        """

        def handle_file(fieldfile: FieldFile, **kwargs):
            should_process = False
            if fields is None:  # Listen to all FieldFiles if fields is None
                should_process = True
            elif isinstance(fields, list):  # List of field names
                if fieldfile.field.name in fields:
                    should_process = True
            elif isinstance(
                fieldfile.field, fields
            ):  # Specific field type (e.g., ImageField)
                should_process = True

            if should_process:
                self(fieldfile, build=build, send_signal=send_signal)

        # Pass dispatch_uid to connect
        file_post_save.connect(
            handle_file, sender=model, weak=False, dispatch_uid=dispatch_uid
        )


class SrcSetItem(NamedTuple):
    """Represents a single item in the generated srcset."""

    thumb: "EasyImage"  # Use string literal for type hint
    # Store the original options used to generate this item for as_html
    options: Options


# Sentinel object to represent unloaded state more explicitly than None
# This helps distinguish between "not loaded" and "loaded, but is None"
_UNLOADED = object()


class BoundImg:
    """
    Represents an Img configuration bound to a specific source file.
    Handles lazy loading and building of EasyImage instances.
    """

    # Type hints for internal state
    _file: FieldFile
    _img: Img
    _build: BuildChoices | None
    _send_signal: bool
    _storage_name: str
    _pk_to_options: dict[UUID, ParsedOptions]  # Maps PK to ParsedOptions for building
    _base_pk: UUID | None
    _srcset_pks: list[UUID]
    _srcset_pk_options: dict[
        UUID, Options
    ]  # Maps PK to original Options for HTML generation
    _sizes_attr: str
    _loaded: bool
    _images: dict[UUID, "EasyImage"]  # Cache for loaded EasyImage instances

    # Public attributes
    alt: str

    def __init__(
        self,
        file: FieldFile,
        *,
        alt: str | None,
        img: Img,
        build: BuildChoices = None,
        send_signal: bool,
    ):
        # Local import to avoid AppRegistryNotReady errors
        from .models import EasyImage, get_storage_name

        # Initialize internal state
        self._file = file
        self._img = img
        self._build = build
        self._send_signal = send_signal
        self._storage_name = get_storage_name(file.storage)
        self._loaded = False
        self._images = {}
        self._pk_to_options = {}
        self._base_pk = None
        self._srcset_pks = []
        self._srcset_pk_options = {}
        self._sizes_attr = ""

        # --- Calculate all required options and PKs ---
        img_options = img.options
        instance = file.instance  # Instance the file belongs to

        base_width: int | None = None
        if "width" in img_options and img_options["width"] is not None:
            # Base image options (always JPEG for preview)
            raw_base_opts = cast(Options, img_options.copy())
            raw_base_opts["mimetype"] = "image/jpeg"
            base_parsed_options = ParsedOptions(instance, **raw_base_opts)
            self._base_pk = EasyImage.objects.hash(
                name=file.name, storage=self._storage_name, options=base_parsed_options
            )
            self._pk_to_options[self._base_pk] = base_parsed_options
            # Store the calculated base width for use in sizes/densities
            base_width = base_parsed_options.width

        # Prepare general options for srcset variations
        densities = list(img_options.get("densities") or [])  # Ensure mutable list
        srcset_base_options = cast(Options, img_options.copy())

        # Determine mimetype for srcset based on format option or source file
        if fmt := img_options.get("format"):
            mime = format_map.get(fmt)
            if mime:
                srcset_base_options["mimetype"] = mime
                # Ensure 1x density exists for non-JPEG formats if densities are used
                if densities and 1 not in densities and mime != "image/jpeg":
                    densities.insert(0, 1)
            else:
                # Fallback to source type if format is invalid
                source_type = mimetypes.guess_type(file.name)[0]
                srcset_base_options["mimetype"] = source_type or "image/jpeg"
        else:
            source_type = mimetypes.guess_type(file.name)[0]
            srcset_base_options["mimetype"] = source_type or "image/jpeg"

        # --- Calculate PKs/Options for 'sizes' attribute ---
        sizes_attr_list: list[str] = []
        sizes = img_options.get("sizes")
        max_width_options: Options | None = (
            None  # Track options for the largest size defined
        )
        max_width_for_density = base_width  # Track the width value of the largest size

        if (
            sizes and base_width is not None
        ):  # 'sizes' requires a base width to be meaningful
            # Start with base options for the max width calculation
            img_opts_for_sizes = srcset_base_options.copy()
            img_opts_for_sizes["srcset_width"] = base_width
            max_width_options = img_opts_for_sizes
            max_width_for_density = base_width

            for media, size_info in sizes.items():
                media_options = srcset_base_options.copy()
                if isinstance(size_info, dict):
                    media_options.update(size_info)
                else:
                    # Handle int or valid WidthChoices string
                    if isinstance(size_info, int):
                        media_options["width"] = size_info
                    elif isinstance(size_info, str):
                        valid_width_choices = get_args(WidthChoices)
                        if size_info in valid_width_choices:
                            # Cast to satisfy type checker that it's a valid literal
                            media_options["width"] = cast(WidthChoices, size_info)
                        else:
                            raise ValueError(
                                f"Invalid string value '{size_info}' for size option. "
                                f"Expected an integer, dict, or one of {valid_width_choices}"
                            )
                    else:
                        # Should not happen based on type hints, but raise error if it does
                        raise TypeError(
                            f"Unexpected type for size option value: {type(size_info)}"
                        )

                parsed_media_options = ParsedOptions(instance, **media_options)
                if not parsed_media_options.width:
                    raise ValueError(
                        f"Size options must resolve to a width: {media_options}"
                    )

                # Store srcset_width in the original options dict for HTML generation
                media_options["srcset_width"] = parsed_media_options.width
                media_pk = EasyImage.objects.hash(
                    name=file.name,
                    storage=self._storage_name,
                    options=parsed_media_options,
                )
                self._pk_to_options[media_pk] = parsed_media_options
                self._srcset_pks.append(media_pk)
                self._srcset_pk_options[media_pk] = (
                    media_options  # Store original options
                )

                media_str = (
                    f"(max-width: {media}px)" if isinstance(media, int) else str(media)
                )
                # Update max_width if this media query defines a larger image
                if (
                    parsed_media_options.width > max_width_for_density
                    and "print" not in media_str
                ):
                    max_width_options = media_options  # Store the options dict
                    max_width_for_density = parsed_media_options.width
                sizes_attr_list.append(f"{media_str} {parsed_media_options.width}px")

            # Add the default size (largest calculated width) to sizes attribute
            sizes_attr_list.append(f"{max_width_for_density}px")

            # Add the EasyImage for the default size if not already added via media query
            if max_width_options:
                parsed_max_opts = ParsedOptions(instance, **max_width_options)
                max_pk = EasyImage.objects.hash(
                    name=file.name, storage=self._storage_name, options=parsed_max_opts
                )
                if max_pk not in self._pk_to_options:
                    self._pk_to_options[max_pk] = parsed_max_opts
                    self._srcset_pks.append(max_pk)
                    self._srcset_pk_options[max_pk] = max_width_options

            # Handle high density based on the determined max_width_options
            max_density = max(densities) if densities else 1
            if max_density > 1 and max_width_options is not None:
                high_density_options = max_width_options.copy()
                high_density_options["width_multiplier"] = max_density
                parsed_high_density = ParsedOptions(instance, **high_density_options)
                high_density_pk = EasyImage.objects.hash(
                    name=file.name,
                    storage=self._storage_name,
                    options=parsed_high_density,
                )
                self._pk_to_options[high_density_pk] = parsed_high_density
                self._srcset_pks.append(high_density_pk)
                self._srcset_pk_options[high_density_pk] = high_density_options

        # --- Calculate PKs/Options for 'densities' (if 'sizes' not used) ---
        elif densities:
            for density in densities:
                density_options = srcset_base_options.copy()
                density_options["width_multiplier"] = density
                parsed_density_opts = ParsedOptions(instance, **density_options)
                density_pk = EasyImage.objects.hash(
                    name=file.name,
                    storage=self._storage_name,
                    options=parsed_density_opts,
                )
                self._pk_to_options[density_pk] = parsed_density_opts
                self._srcset_pks.append(density_pk)
                self._srcset_pk_options[density_pk] = density_options

        self._sizes_attr = ", ".join(sizes_attr_list)

        # --- Determine Queued Status (needs creation?) ---
        queued = False
        all_pks = list(self._pk_to_options.keys())
        if all_pks:
            # Check which PKs already exist in the database
            existing_pks = set(
                EasyImage.objects.filter(pk__in=all_pks).values_list("pk", flat=True)
            )
            if set(all_pks) - existing_pks:
                # If there are PKs that don't exist, mark as queued
                queued = True

        # --- Handle Alt Text ---
        if isinstance(alt, str):
            self.alt = alt
        elif "alt" in img_options and isinstance(img_options["alt"], str):
            self.alt = img_options["alt"]
        else:
            self.alt = ""  # Default to empty alt text

        # --- Trigger Signal if Queued ---
        if queued and send_signal:
            # Pass self (BoundImg instance) as the instance needing processing
            queued_img.send(sender=self.__class__, instance=self)

        # --- Handle Immediate Build Request ---
        if build:
            self._load_images()  # Ensure instances are loaded/created
            self._build_images(build)  # Trigger the build process

    def _load_images(self):
        """
        Internal method to lazy-load EasyImage objects from the database.
        Uses the bulk `from_pks` manager method.
        """
        if self._loaded:  # Avoid reloading if already done
            return

        if not self._pk_to_options:  # No images to load
            self._loaded = True
            return

        # Local import
        from .models import EasyImage

        # Fetch existing and create missing EasyImage objects in bulk
        self._images = EasyImage.objects.from_pks(
            self._pk_to_options, self._file.name, self._storage_name
        )
        self._loaded = True

    def _build_images(self, build_choice: BuildChoices):
        """
        Internal method to build the actual image files based on the build choice.
        Requires images to be loaded first via _load_images().
        """
        # Local imports
        from . import engine
        from .models import EasyImage, ImageStatus

        build_targets: list[tuple[EasyImage, ParsedOptions]] = []

        # Determine which images need building based on build_choice
        if build_choice == "srcset":
            # Add only srcset images needing build
            for pk in self._srcset_pks:
                img_instance = self._images.get(pk)
                # Check instance exists, image field is empty, and options exist
                if (
                    img_instance
                    and not img_instance.image
                    and pk in self._pk_to_options
                ):
                    build_targets.append((img_instance, self._pk_to_options[pk]))
        elif build_choice == "src":
            # Add only base image needing build
            if self._base_pk:
                img_instance = self._images.get(self._base_pk)
                # Check instance exists, image field is empty, and options exist
                if (
                    img_instance
                    and not img_instance.image
                    and self._base_pk in self._pk_to_options
                ):
                    build_targets.append(
                        (img_instance, self._pk_to_options[self._base_pk])
                    )
        elif build_choice == "all":
            # Add all images needing build
            for pk, img_instance in self._images.items():
                # Check instance exists, image field is empty, and options exist
                if (
                    img_instance
                    and not img_instance.image
                    and pk in self._pk_to_options
                ):
                    build_targets.append((img_instance, self._pk_to_options[pk]))
        # If build_choice is None or other invalid value, build_targets remains empty

        if not build_targets:
            return  # Nothing to build

        try:
            # Load the source image efficiently for all targets
            source_img = engine.efficient_load(
                file=self._file, options=[opts for _, opts in build_targets]
            )
        except Exception:
            # Mark all targeted EasyImage instances as having a source error
            now = timezone.now()
            pks_to_update = [im.pk for im, _ in build_targets]
            EasyImage.objects.filter(pk__in=pks_to_update).update(
                error_count=F("error_count") + 1,
                status=ImageStatus.SOURCE_ERROR,
                status_changed_date=now,
            )
            # Update local status in the cache as well
            for im, _ in build_targets:
                if im:  # Check if image instance exists in cache
                    im.status = ImageStatus.SOURCE_ERROR
                    im.status_changed_date = now
                    im.error_count += 1
        else:
            # Build each target image
            for im, opts in build_targets:
                if not im:
                    continue  # Skip if image instance somehow missing

                # Reload the instance fields related to build status before building
                # This minimizes race conditions if status changed elsewhere.
                try:
                    im.refresh_from_db(
                        fields=["status", "status_changed_date", "image"]
                    )
                except EasyImage.DoesNotExist:
                    continue  # Skip if deleted since loading

                # Call the build method on the EasyImage instance
                im.build(source_img=source_img, options=opts)

    @property
    def base(self) -> "EasyImage | None":  # Use string literal for type hint
        """Lazy-loading property for the base EasyImage instance."""
        self._load_images()  # Ensure images are loaded
        if self._base_pk:
            return self._images.get(self._base_pk)  # Return from cache
        return None

    @property
    def srcset(self) -> list["SrcSetItem"]:  # Use string literal for type hint
        """Lazy-loading property for the list of SrcSetItem tuples."""
        self._load_images()  # Ensure images are loaded
        srcset_list: list[SrcSetItem] = []
        for pk in self._srcset_pks:
            thumb = self._images.get(pk)
            # Only include if the thumb exists in cache and has been successfully built
            if thumb and thumb.image:
                # Retrieve the original options used for this specific srcset item
                original_options = self._srcset_pk_options.get(pk)
                if (
                    original_options
                ):  # Should always exist if pk is in _srcset_pk_options
                    srcset_list.append(
                        SrcSetItem(thumb=thumb, options=original_options)
                    )
        return srcset_list

    @property
    def sizes(self) -> str:
        """Returns the calculated sizes attribute string."""
        # This is calculated in __init__ and doesn't require loading images
        return self._sizes_attr

    def as_html(self) -> str:
        """Generate the complete <img> tag HTML with srcset and sizes."""
        srcset_parts = []
        # Access the lazy-loaded srcset property (triggers _load_images if needed)
        current_srcset = self.srcset
        for item in current_srcset:
            # item.options holds the original Options dict used for this item
            options = item.options
            # Ensure the thumb has a URL before proceeding
            if not item.thumb.image or not hasattr(item.thumb.image, "url"):
                continue  # Skip if image file doesn't exist or has no URL

            srcset_str = item.thumb.image.url
            if w := options.get("srcset_width"):
                # Apply width multiplier if it exists in the original options
                if mult := options.get("width_multiplier"):
                    # Ensure w is treated as a number for multiplication
                    try:
                        # Use float for potentially fractional multipliers
                        w_val = float(w)
                        mult_val = float(mult)
                        w = int(w_val * mult_val)  # Final width descriptor is integer
                    except (ValueError, TypeError):
                        pass  # Keep original w if conversion fails
                srcset_str += f" {w}w"
            elif mult := options.get("width_multiplier"):
                # Handle density descriptor (e.g., " 2x")
                if mult != 1:
                    # Use :g for float formatting to handle integers cleanly (e.g., "2x" not "2.0x")
                    srcset_str += f" {mult:g}x"
            srcset_parts.append(srcset_str)

        # Access the lazy-loaded base property via base_url (triggers _load_images if needed)
        src = self.base_url()

        # Get image attributes from the original Img config
        img_attrs_config = self._img.options.get("img_attrs")
        img_attrs = img_attrs_config.copy() if img_attrs_config else {}

        # Set core attributes
        img_attrs["src"] = src
        if srcset_parts:
            img_attrs["srcset"] = ", ".join(srcset_parts)
            # Access the sizes property
            if self.sizes:
                img_attrs["sizes"] = self.sizes

        img_attrs["alt"] = self.alt  # Use the alt text determined in __init__

        # Format attributes into HTML string
        attrs = " ".join(
            (
                f'{k}="{escape(v)}"' if v is not True else k
            )  # Handle boolean attributes like 'ismap'
            for k, v in img_attrs.items()
            if v is not None  # Skip None values
        )
        return f"<img {attrs}>"

    def base_url(self) -> str:
        """
        Return the URL for the base EasyImage instance,
        or the original source file URL if the base doesn't exist or isn't built.
        """
        # Access the lazy-loaded base property (triggers _load_images if needed)
        base_image = self.base
        if base_image and base_image.image and hasattr(base_image.image, "url"):
            return base_image.image.url
        # Fallback to the original source file URL
        return self._file.url

    def __str__(self) -> str:
        """String representation defaults to the base URL."""
        return self.base_url()
