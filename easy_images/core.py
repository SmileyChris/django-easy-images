from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING, Any, NamedTuple, cast, get_args
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

    _batch: "ImageBatch | None"

    def __init__(
        self, batch: "ImageBatch | None" = None, **options: Unpack[ImgOptions]
    ):
        all_options = option_defaults.copy()
        all_options.update(options)
        self.options = all_options
        self._batch = batch  # Store batch reference, None by default

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
        immediate: bool = False,
    ) -> "BoundImg":  # Return new BoundImg
        """Add this image configuration to the batch for processing."""
        # Create a fresh batch if none exists (avoids memory leaks)
        batch = self._batch or ImageBatch()
        return batch.add(
            source_file=source,
            img=self,
            alt=alt,
            build=build,
            send_signal=send_signal,
            immediate=immediate,
        )

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
                self(fieldfile, build=build, send_signal=send_signal, immediate=True)

        # Pass dispatch_uid to connect
        file_post_save.connect(
            handle_file, sender=model, weak=False, dispatch_uid=dispatch_uid
        )


class SrcSetItem(NamedTuple):
    """
    Represents a single item in the generated srcset.
    """

    thumb: "EasyImage"
    options: Options  # Original options used for this item


class ImageBatch:
    """
    Manages a collection of image items for batched loading.
    """

    def __init__(self):
        self._is_loaded: bool = False
        self._all_pk_to_options: dict[UUID, ParsedOptions] = {}
        self._loaded_images: dict[UUID, "EasyImage"] = {}
        # Maps item_id -> {details: dict}
        self._batch_items: dict[int, dict] = {}
        self._next_item_id: int = 0
        # Store source file info needed for loading missing images
        # Maps (name, storage_name) -> FieldFile (or just necessary info)
        self._source_files: dict[tuple[str, str], FieldFile] = {}

    def add(
        self,
        source_file: FieldFile,
        img: Img,
        alt: str | None = None,
        build: BuildChoices = None,
        send_signal=False,
        immediate: bool = False,
    ) -> "BoundImg":
        """
        Adds an image item to the batch.
        """
        # Local import inside method to avoid circular dependency issues at import time
        from .models import EasyImage, get_storage_name

        item_id = self._next_item_id
        self._next_item_id += 1

        storage_name = get_storage_name(source_file.storage)
        source_key = (source_file.name, storage_name)
        if source_key not in self._source_files:
            self._source_files[source_key] = source_file  # Store the FieldFile itself

        # --- Calculate PKs and Options ---
        # This logic needs to be extracted and potentially refactored for clarity
        item_pk_to_options: dict[UUID, ParsedOptions] = {}
        item_base_pk: UUID | None = None
        item_srcset_pks: list[UUID] = []
        item_srcset_pk_options: dict[UUID, Options] = {}
        item_sizes_attr_list: list[str] = []
        instance = source_file.instance

        base_width: int | None = None
        if "width" in img.options and img.options["width"] is not None:
            raw_base_opts = cast(Options, img.options.copy())
            raw_base_opts["mimetype"] = "image/jpeg"
            base_parsed_options = ParsedOptions(instance, **raw_base_opts)
            item_base_pk = EasyImage.objects.hash(
                name=source_file.name, storage=storage_name, options=base_parsed_options
            )
            item_pk_to_options[item_base_pk] = base_parsed_options
            base_width = base_parsed_options.width

        densities = list(img.options.get("densities") or [])
        srcset_base_options = cast(Options, img.options.copy())

        if fmt := img.options.get("format"):
            mime = format_map.get(fmt)
            if mime:
                srcset_base_options["mimetype"] = mime
                if densities and 1 not in densities and mime != "image/jpeg":
                    densities.insert(0, 1)
            else:
                source_type = mimetypes.guess_type(source_file.name)[0]
                srcset_base_options["mimetype"] = source_type or "image/jpeg"
        else:
            source_type = mimetypes.guess_type(source_file.name)[0]
            srcset_base_options["mimetype"] = source_type or "image/jpeg"

        sizes = img.options.get("sizes")
        max_width_options: Options | None = None
        max_width_for_density = base_width

        if sizes and base_width is not None:
            img_opts_for_sizes = srcset_base_options.copy()
            img_opts_for_sizes["srcset_width"] = base_width
            max_width_options = img_opts_for_sizes
            max_width_for_density = base_width

            for media, size_info in sizes.items():
                media_options = srcset_base_options.copy()
                if isinstance(size_info, dict):
                    media_options.update(size_info)
                else:
                    if isinstance(size_info, int):
                        media_options["width"] = size_info
                    elif isinstance(size_info, str):
                        valid_choices = get_args(WidthChoices)
                        if size_info in valid_choices:
                            media_options["width"] = cast(WidthChoices, size_info)
                        else:
                            raise ValueError(
                                f"Invalid string '{size_info}' for size. Expected int, dict, or {valid_choices}"
                            )
                    else:
                        raise TypeError(
                            f"Unexpected type for size option: {type(size_info)}"
                        )

                parsed_media_options = ParsedOptions(instance, **media_options)
                if not parsed_media_options.width:
                    raise ValueError(
                        f"Size options must resolve to width: {media_options}"
                    )

                media_options["srcset_width"] = parsed_media_options.width
                media_pk = EasyImage.objects.hash(
                    name=source_file.name,
                    storage=storage_name,
                    options=parsed_media_options,
                )
                item_pk_to_options[media_pk] = parsed_media_options
                item_srcset_pks.append(media_pk)
                item_srcset_pk_options[media_pk] = media_options

                media_str = (
                    f"(max-width: {media}px)" if isinstance(media, int) else str(media)
                )
                if (
                    parsed_media_options.width > max_width_for_density
                    and "print" not in media_str
                ):
                    max_width_options = media_options
                    max_width_for_density = parsed_media_options.width
                item_sizes_attr_list.append(
                    f"{media_str} {parsed_media_options.width}px"
                )

            item_sizes_attr_list.append(f"{max_width_for_density}px")

            if max_width_options:
                parsed_max_opts = ParsedOptions(instance, **max_width_options)
                max_pk = EasyImage.objects.hash(
                    name=source_file.name, storage=storage_name, options=parsed_max_opts
                )
                if max_pk not in item_pk_to_options:
                    item_pk_to_options[max_pk] = parsed_max_opts
                    item_srcset_pks.append(max_pk)
                    item_srcset_pk_options[max_pk] = max_width_options

            max_density = max(densities) if densities else 1
            if max_density > 1 and max_width_options is not None:
                high_density_options = max_width_options.copy()
                high_density_options["width_multiplier"] = max_density
                parsed_high_density = ParsedOptions(instance, **high_density_options)
                high_density_pk = EasyImage.objects.hash(
                    name=source_file.name,
                    storage=storage_name,
                    options=parsed_high_density,
                )
                item_pk_to_options[high_density_pk] = parsed_high_density
                item_srcset_pks.append(high_density_pk)
                item_srcset_pk_options[high_density_pk] = high_density_options

        elif densities:
            for density in densities:
                density_options = srcset_base_options.copy()
                density_options["width_multiplier"] = density
                parsed_density_opts = ParsedOptions(instance, **density_options)
                density_pk = EasyImage.objects.hash(
                    name=source_file.name,
                    storage=storage_name,
                    options=parsed_density_opts,
                )
                item_pk_to_options[density_pk] = parsed_density_opts
                item_srcset_pks.append(density_pk)
                item_srcset_pk_options[density_pk] = density_options

        item_sizes_attr = ", ".join(item_sizes_attr_list)
        # --- End PK/Option Calculation ---

        # Store item details
        self._batch_items[item_id] = {
            "source_name": source_file.name,
            "storage_name": storage_name,
            "alt": alt if isinstance(alt, str) else img.options.get("alt", ""),
            "build": build,  # Store build choice for later use
            "send_signal": send_signal,
            "pk_to_options": item_pk_to_options,
            "base_pk": item_base_pk,
            "srcset_pks": item_srcset_pks,
            "srcset_pk_options": item_srcset_pk_options,
            "sizes_attr": item_sizes_attr,
            "source_name_fallback": source_file.name,  # Store original name for fallback
        }

        # Merge this item's PKs into the batch-wide collection
        # Check if we're adding new PKs that weren't in the batch before
        new_pks = set(item_pk_to_options.keys()) - set(
            self._all_pk_to_options.keys()
        )
        self._all_pk_to_options.update(item_pk_to_options)

        # If we added new PKs to an already-loaded batch, reset _is_loaded
        # so _ensure_loaded() will process the new images
        if new_pks and self._is_loaded:
            self._is_loaded = False

        # Build intent is stored in item data, executed later via batch.build()
        # However, if immediate=True (used by queue/signals), build right away
        if build and immediate:
            self._ensure_loaded()
            self.build_images_for_item(item_id, build)

        # --- Handle Signal ---
        # Check if any of the calculated PKs for *this specific item* already exist.
        # If none exist and send_signal is True, it means this is the first time
        # we're encountering this image configuration, so send the signal.
        bound_img = BoundImg(self, item_id)  # Create instance first
        if send_signal:
            item_pks = list(item_pk_to_options.keys())
            if item_pks:  # Only check DB if there are PKs to check
                # Check if *any* of these PKs exist. If the count is 0, none exist.
                if not EasyImage.objects.filter(pk__in=item_pks).exists():
                    # Pass the BoundImg instance itself, mimicking old behavior
                    queued_img.send(sender=BoundImg, instance=bound_img)

        return bound_img

    def _ensure_loaded(self):
        """Loads EasyImage data from DB for all items in the batch."""
        if self._is_loaded:
            return

        # Local import
        from .models import EasyImage, ImageStatus  # Add ImageStatus

        all_pks = list(self._all_pk_to_options.keys())
        if not all_pks:
            self._is_loaded = True
            return

        # Only query for PKs we don't already have loaded
        already_loaded_pks = set(self._loaded_images.keys())
        pks_to_query = [pk for pk in all_pks if pk not in already_loaded_pks]

        if pks_to_query:
            new_images = {
                img.pk: img for img in EasyImage.objects.filter(pk__in=pks_to_query)
            }
            # Merge new images with existing ones
            existing_images = {**self._loaded_images, **new_images}
        else:
            # No new PKs to query, use existing loaded images
            existing_images = self._loaded_images.copy()

        missing_pks = set(all_pks) - set(existing_images.keys())

        new_instances_to_create: list[EasyImage] = []
        pks_that_were_missing: set[UUID] = set()  # Track which PKs we attempt to create

        if missing_pks:
            # Group missing PKs by their original source file info to create instances correctly
            missing_grouped: dict[tuple[str, str], list[UUID]] = {}
            pk_to_source_key: dict[UUID, tuple[str, str]] = {}

            for item_id, item_data in self._batch_items.items():
                source_key = (item_data["source_name"], item_data["storage_name"])
                for pk in item_data.get("pk_to_options", {}):
                    if pk in missing_pks:
                        pk_to_source_key[pk] = source_key
                        if source_key not in missing_grouped:
                            missing_grouped[source_key] = []
                        missing_grouped[source_key].append(pk)

            # Create instances for each group
            for (name, storage), pks_in_group in missing_grouped.items():
                for pk in pks_in_group:
                    options = self._all_pk_to_options[pk]
                    new_instances_to_create.append(
                        EasyImage(
                            pk=pk,
                            storage=storage,
                            name=name,
                            args=options.to_dict(),
                            # status defaults to QUEUED
                        )
                    )
                    pks_that_were_missing.add(
                        pk
                    )  # Mark this PK as one we tried to create

            if new_instances_to_create:
                # Use ignore_conflicts=True for race conditions
                created_instances = EasyImage.objects.bulk_create(
                    new_instances_to_create, ignore_conflicts=True
                )
                # Update cache with successfully created instances
                existing_images.update({img.pk: img for img in created_instances})

                # If ignore_conflicts happened, some instances in new_instances_to_create
                # might not be in created_instances. We need to re-fetch them.
                created_pks = {img.pk for img in created_instances}
                refetch_pks = pks_that_were_missing - created_pks
                if refetch_pks:
                    refetched_images = {
                        img.pk: img
                        for img in EasyImage.objects.filter(pk__in=refetch_pks)
                    }
                    existing_images.update(refetched_images)

        self._loaded_images = existing_images
        self._is_loaded = True

        # --- Handle Signals for Newly Created/Relevant Images ---
        # Iterate through items and check if any of their PKs were missing AND send_signal is True
        pks_needing_signal = set()
        for item_id, item_data in self._batch_items.items():
            if item_data.get("send_signal"):
                item_pks = set(item_data.get("pk_to_options", {}).keys())
                # Check if any of this item's PKs were among those we attempted to create
                if item_pks.intersection(pks_that_were_missing):
                    # Add all PKs for this item to the signal list? Or just the missing ones?
                    # Let's add all PKs associated with the item that triggered the signal.
                    pks_needing_signal.update(item_pks)

        if pks_needing_signal:
            # Send one signal with all relevant EasyImage instances?
            # The signal expects a single instance. We might need a new signal
            # or send multiple signals. Let's send multiple for now.
            relevant_instances = [
                img
                for pk, img in self._loaded_images.items()
                if pk in pks_needing_signal
            ]
            for instance in relevant_instances:
                # Check if the instance status indicates it needs building (e.g., still QUEUED)
                # Refresh status just in case bulk_create didn't return the absolute latest
                try:
                    instance.refresh_from_db(fields=["status"])
                except EasyImage.DoesNotExist:
                    continue  # Skip if deleted somehow

                if instance.status == ImageStatus.QUEUED:
                    # Pass the EasyImage instance itself to the signal
                    queued_img.send(sender=EasyImage, instance=instance)

    def get_image(self, pk: UUID) -> "EasyImage | None":
        """
        Retrieves a loaded EasyImage instance from the cache.
        """
        # Ensure loaded? Or assume _ensure_loaded was called by BoundImg?
        # For safety, call it, but it will return quickly if already loaded.
        self._ensure_loaded()
        return self._loaded_images.get(pk)

    def build_images_for_item(self, item_id: int, build_choice: BuildChoices):
        """
        Builds images for a specific item ID within the batch.
        """
        # Local imports
        from . import engine
        from .models import EasyImage, ImageStatus

        self._ensure_loaded()  # Make sure models are loaded/created

        item_data = self._batch_items.get(item_id)
        if not item_data:
            print(f"Warning: Item ID {item_id} not found in batch.")
            return  # Item not found

        source_name = item_data["source_name"]
        storage_name = item_data["storage_name"]
        source_key = (source_name, storage_name)
        source_file = self._source_files.get(source_key)

        if not source_file:
            print(f"Warning: Source file info missing for {source_key} in batch.")
            # TODO: Handle error - maybe try to open from storage?
            return

        pk_to_options = item_data.get("pk_to_options", {})
        base_pk = item_data.get("base_pk")
        srcset_pks = item_data.get("srcset_pks", [])

        build_targets_pks: list[UUID] = []

        # Determine target PKs based on build_choice
        if build_choice == "srcset":
            build_targets_pks.extend(srcset_pks)
        elif build_choice == "src":
            if base_pk:
                build_targets_pks.append(base_pk)
        elif build_choice == "all":
            build_targets_pks.extend(pk_to_options.keys())
        # If build_choice is None, build_targets_pks remains empty

        build_targets: list[tuple[EasyImage, ParsedOptions]] = []
        pks_to_build_locally: set[UUID] = set()  # Track PKs we intend to build now

        for pk in build_targets_pks:
            img_instance = self._loaded_images.get(pk)
            options = pk_to_options.get(pk)
            # Check instance exists, options exist, and image field is not yet populated
            if img_instance and options and not img_instance.image:
                # Check status - avoid building if already building or errored?
                # Let EasyImage.build handle status checks internally for atomicity.
                build_targets.append((img_instance, options))
                pks_to_build_locally.add(pk)

        if not build_targets:
            # print(f"No images to build for item {item_id} with choice '{build_choice}'")
            return  # Nothing to build for this item/choice

        # --- Perform Build (Adapted from old BoundImg._build_images) ---
        source_img: "engine.Image | None" = None
        try:
            # Load the source image efficiently just once for all targets in this item
            source_img = engine.efficient_load(
                file=source_file, options=[opts for _, opts in build_targets]
            )
        except Exception as e:
            print(f"Error loading source image {source_file.name}: {e}")
            # Mark all targeted EasyImage instances as having a source error
            now = timezone.now()
            EasyImage.objects.filter(pk__in=list(pks_to_build_locally)).update(
                error_count=F("error_count") + 1,
                status=ImageStatus.SOURCE_ERROR,
                status_changed_date=now,
            )
            # Update local status in the cache as well
            for im, _ in build_targets:
                if im:  # Check instance exists in cache
                    im.status = ImageStatus.SOURCE_ERROR
                    im.status_changed_date = now
                    im.error_count += 1
        else:
            # Build each target image if source loaded successfully
            for im, opts in build_targets:
                if not im:
                    continue  # Should not happen if build_targets is constructed correctly

                # Call the build method on the EasyImage instance
                # Pass the pre-loaded source_img.
                # The build method handles its own status updates and saving.
                built_ok = im.build(source_img=source_img, options=opts)
                # Refresh the instance in the cache if build was successful
                # to ensure the .image field (and .url) is populated.
                if built_ok:
                    try:
                        # Re-fetch the instance from DB to ensure we have the saved state
                        refreshed_im = EasyImage.objects.get(pk=im.pk)
                        # Update the cache with the re-fetched instance
                        self._loaded_images[refreshed_im.pk] = refreshed_im
                    except EasyImage.DoesNotExist:
                        # Instance might have been deleted concurrently, ignore.
                        pass

    def build(self):
        """
        Execute all build items in the batch efficiently.

        This method processes all images that were added with a build parameter,
        performing batch database operations first, then building each image
        according to its specified build choice.
        """
        # Ensure all DB records are loaded/created efficiently in one batch operation
        self._ensure_loaded()

        # Build images for each item that specified a build option
        for item_id, item_data in self._batch_items.items():
            build_choice = item_data.get("build")
            if build_choice:  # Only build if build was specified during add()
                self.build_images_for_item(item_id, build_choice)


class BoundImg:
    """
    Represents a single image item within a batch. Accessing properties
    triggers the batch loading mechanism if not already loaded.
    """

    _parent_batch: "ImageBatch"
    _item_id: int

    def __init__(self, parent_batch: "ImageBatch", item_id: int):
        self._parent_batch = parent_batch
        self._item_id = item_id

    # Add more specific type hints using TypeVar or overload if needed,
    # but for now, basic Any helps Pylance a bit.
    def _get_item_detail(self, key: str, default: Any = None) -> Any:
        """Helper to get details for this specific item from the batch."""
        item_data = self._parent_batch._batch_items.get(self._item_id, {})
        return item_data.get(key, default)

    def _ensure_batch_built(self):
        """Ensure this BoundImg has been built if it needs building."""
        # Always ensure DB records are loaded first
        self._parent_batch._ensure_loaded()

        build_choice = self._get_item_detail("build")
        if build_choice and not self.is_built:
            self._parent_batch.build_images_for_item(self._item_id, build_choice)

    @property
    def is_built(self) -> bool:
        """Check if the item's images have been built.

        Returns True if the images specified by the build parameter have been
        successfully built and stored in the database.
        """
        # Access underlying data without triggering auto-building to avoid recursion
        self._parent_batch._ensure_loaded()  # Just ensure DB records exist

        build_choice = self._get_item_detail("build")
        if not build_choice:
            return True  # No build requested, consider it "built"

        if build_choice == "src":
            base_pk = self._get_item_detail("base_pk")
            if base_pk:
                base_img = self._parent_batch.get_image(base_pk)
                # Simply check if the image field is populated (not None/empty)
                # This avoids file I/O and is sufficient for our needs
                return bool(base_img and base_img.image)
        elif build_choice == "srcset":
            srcset_pks = self._get_item_detail("srcset_pks", []) or []
            # Just check if any srcset images have been built
            for pk in srcset_pks:
                thumb = self._parent_batch.get_image(pk)
                if thumb and thumb.image:
                    return True  # At least one is built
            return False
        elif build_choice == "all":
            # Check if we have PKs to check
            base_pk = self._get_item_detail("base_pk")
            srcset_pks = self._get_item_detail("srcset_pks", []) or []

            # Check base if exists
            if base_pk:
                base_img = self._parent_batch.get_image(base_pk)
                if base_img and base_img.image:
                    return True

            # Check srcset if exists
            for pk in srcset_pks:
                thumb = self._parent_batch.get_image(pk)
                if thumb and thumb.image:
                    return True

            return False
        return False

    @property
    def alt(self) -> str:
        # Alt text is stored directly, no loading needed initially
        return self._get_item_detail("alt", "")

    @property
    def base(self) -> "EasyImage | None":
        self._ensure_batch_built()  # Auto-build if needed
        base_pk = self._get_item_detail("base_pk")
        if base_pk:
            # Use the batch's getter which handles the cache
            return self._parent_batch.get_image(base_pk)
        return None

    @property
    def srcset(self) -> list[SrcSetItem]:  # Use the new SrcSetItem defined below
        self._ensure_batch_built()  # Auto-build if needed
        srcset_items: list[SrcSetItem] = []
        # Provide a default empty list to satisfy type checker for iteration
        srcset_pks = self._get_item_detail("srcset_pks", []) or []
        # Need original options used for each srcset item for correct HTML/info
        srcset_pk_options = self._get_item_detail("srcset_pk_options", {})

        for pk in srcset_pks:
            # Use the batch's getter
            thumb = self._parent_batch.get_image(pk)
            # Only include if the thumb exists in cache and has been successfully built
            if thumb and thumb.image:
                original_options = srcset_pk_options.get(pk)
                if (
                    original_options
                ):  # Should always exist if pk is in _srcset_pk_options
                    srcset_items.append(
                        SrcSetItem(thumb=thumb, options=original_options)
                    )
        return srcset_items

    @property
    def sizes(self) -> str:
        # Sizes attribute string is calculated and stored during add()
        # Ensure a string is returned
        return str(self._get_item_detail("sizes_attr", ""))

    def as_html(self, img_attrs: dict[str, str] | None = None) -> str:
        """Generate the complete <img> tag HTML with srcset and sizes.

        :param img_attrs: Optional dict of additional attributes to add to the <img> tag.
        """
        # Accessing properties triggers loading if needed
        base_img = self.base
        srcset_items = self.srcset
        sizes_attr = self.sizes
        alt_text = self.alt

        # Build srcset string
        srcset_parts = []
        for item in srcset_items:
            # Ensure the image file exists and width info is available
            if item.thumb.image:
                # Use the width calculated and stored in the original options
                width_desc = item.options.get("srcset_width", item.thumb.width)
                if width_desc:
                    try:
                        # Accessing .url might fail if file is missing
                        srcset_parts.append(f"{item.thumb.image.url} {width_desc}w")
                    except (ValueError, FileNotFoundError):  # Catch potential errors
                        pass  # Skip this srcset item if URL fails
        srcset_str = ", ".join(srcset_parts)

        # Build attributes list
        attrs = []
        # Use base_url() which handles built URL and fallback
        src_url = self.base_url()
        if src_url:
            attrs.append(f'src="{escape(src_url)}"')

        attrs.append(f'alt="{escape(alt_text)}"')
        if srcset_str:
            attrs.append(f'srcset="{escape(srcset_str)}"')
        if sizes_attr:
            attrs.append(f'sizes="{escape(sizes_attr)}"')

        # Add width/height from base image if available and URL was successful
        if src_url and base_img:  # Only add width/height if src was added
            if base_img.width is not None:
                attrs.append(f'width="{base_img.width}"')
            if base_img.height is not None:
                attrs.append(f'height="{base_img.height}"')

        # Add any extra attributes from img_attrs
        if img_attrs:
            for k, v in img_attrs.items():
                # Avoid overwriting existing attributes
                if k and v and not any(attr.startswith(f"{k}=") for attr in attrs):
                    attrs.append(f'{escape(k)}="{escape(v)}"')

        # Filter out potential empty strings if base image failed etc.
        attrs = [attr for attr in attrs if attr]

        return f"<img {' '.join(attrs)}>"

    def base_url(self) -> str:
        """
        Return the URL of the base image, falling back to the original source URL.
        """
        base_img = self.base  # Triggers load
        if base_img and base_img.image:
            try:
                # Attempt to get the URL of the built image
                img_url = base_img.image.url
                return img_url
            except (ValueError, FileNotFoundError):
                pass  # Fall through to original URL if built image URL fails

        # Fallback: Try getting the URL from the original source file object
        try:
            source_name = self._get_item_detail("source_name_fallback")
            storage_name = self._get_item_detail("storage_name")
            if source_name and storage_name:
                source_key = (source_name, storage_name)
                original_file = self._parent_batch._source_files.get(source_key)
                if original_file and hasattr(original_file, "url"):
                    return original_file.url
        except (AttributeError, ValueError):
            # If accessing original file or its URL fails, return empty string
            pass

        return ""  # Ultimate fallback

    def build(self, build_choice: BuildChoices = "all"):
        """
        Triggers the build process for this specific image item within the batch.
        """
        # Delegate building to the parent batch, passing our item ID
        self._parent_batch.build_images_for_item(self._item_id, build_choice)

    def __str__(self) -> str:
        """
        Return the base image URL.
        """
        return self.base_url()

    def __bool__(self) -> bool:
        """
        Return True if the base image exists and has a file.
        """
        # This needs to trigger loading to check the actual image file
        base_img = self.base
        try:
            # Check image attribute and then try accessing file
            return bool(base_img and base_img.image and base_img.image.file)
        except (ValueError, FileNotFoundError):  # Ensure FileNotFoundError is imported
            # If accessing .file raises error (e.g., missing), return False
            return False
