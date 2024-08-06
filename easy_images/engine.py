from __future__ import annotations

import io
import math
import os
from mimetypes import guess_type
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.db.models.fields.files import FieldFile

from easy_images.core import ParsedOptions

if TYPE_CHECKING:
    from pyvips import Image


def scale_image(
    img: Image,
    target: tuple[int, int],
    /,
    crop: tuple[float, float] | bool | None = None,
    contain: bool = False,
    focal_window: tuple[float, float, float, float] | None = None,
):
    """
    Scale an image to the given dimensions, optionally cropping it around a focal point
    or a focal window.
    """
    w, h = img.width, img.height

    if crop:
        contain = False

    if contain:
        # Size image to contain the dimensions, also avoiding upscaling
        scale = min(target[0] / w, target[1] / h, 1)
    else:
        # Scale the image to cover the dimensions
        scale = max(target[0] / w, target[1] / h)

    # Focal window scaling
    if focal_window:
        f_left = focal_window[0] * w
        f_right = focal_window[2] * w
        f_top = focal_window[1] * h
        f_bottom = focal_window[3] * h
        # If the focal window is larger than the target, crop the image to the focal
        # window and scale it down to the target size.
        if f_right - f_left > target[0] and f_bottom - f_top > target[1]:
            img = img.extract_area(f_left, f_top, f_right - f_left, f_bottom - f_top)
            w, h = img.width, h
            if contain:
                scale = min(target[0] / w, target[1] / h, 1)
            else:
                scale = max(target[0] / w, target[1] / h)
            focal_window = None
        # Otherwise, if cropping then set the crop focal point to the center of the
        # focal window.
        elif crop is True:
            crop = (
                (f_left + f_right) / 2,
                (f_top + f_bottom) / 2,
            )

    img = img.resize(scale)
    w, h = img.width, img.height

    if not crop:
        return img

    if crop is True:
        crop = (0.5, 0.5)

    # Calculate the coordinates of the cropping box
    if focal_window:
        focal_point = (
            int(focal_window[0] + crop[0] * (focal_window[2] - focal_window[0]) / 2),
            int(focal_window[1] + crop[1] * (focal_window[3] - focal_window[1]) / 2),
        )
    else:
        focal_point = (
            int(crop[0] * w),
            int(crop[1] * h),
        )
    left = focal_point[0] - target[0] // 2
    top = focal_point[1] - target[1] // 2
    right = left + target[0]
    bottom = top + target[1]

    # Make sure the cropping box is within the image, otherwise move it.
    if left < 0:
        right -= left
        left = 0
    elif right > w:
        left -= right - w
        right = w
    if top < 0:
        bottom -= top
        top = 0
    elif bottom > h:
        top -= bottom - h
        bottom = h
    return img.extract_area(left, top, right - left, bottom - top)


def efficient_load(
    file: str | Path | File, options: list[ParsedOptions] | ParsedOptions | None
) -> Image:
    """
    Load an image from a file, using the most efficient method available.

    Pass a list of target sizes as tuples of ``(width, height)`` or ``(width_ratio,
    height_ratio)`` and the image will be loaded (optimally shrunk to at least 3x the
    largest target size if possible).
    """
    if options and not isinstance(options, list):
        options = [options]
    # Use random access if there are multiple target sizes, since the source image will
    # be used multiple times.
    access = "random" if options and len(options) > 1 else "sequential"
    img = _new_image(file, access=access)
    if not options:
        return img
    x_scale = img.width / max(opt.source_x(img.width) for opt in options)
    y_scale = img.height / max(opt.source_y(img.height) for opt in options)
    min_scale = min(x_scale, y_scale) / 3  # At least 3x of the target size
    if min_scale < 2:
        return img
    shrink = min(2 ** (math.floor(math.log(min_scale, 2))), 8)
    return _new_image(file, shrink=shrink, access=access)


def _new_image(file: str | Path | File, access, **kwargs):
    from pyvips import Image

    path = None
    if isinstance(file, File):
        if isinstance(file, FieldFile):
            try:
                path = file.path
            except Exception:
                pass
        elif isinstance(file, TemporaryUploadedFile):
            path = file.temporary_file_path()
        if not path:
            path = getattr(file, "path", None)
        if not path:
            content = file.read()
            if file.seekable():
                file.seek(0)
            return Image.new_from_buffer(content, "", access=access, **kwargs)
    else:
        path = str(file)
    return Image.new_from_file(path, access=access, **kwargs)


def vips_to_django(
    vips_image: Image, name: str, quality: int = 80
) -> TemporaryUploadedFile | InMemoryUploadedFile:
    """
    Convert a PyVips image to a Django file.
    """
    try:
        temp_file = TemporaryUploadedFile(
            name=name,
            size=0,
            content_type=guess_type(name)[0],
            charset=None,
        )
    except OSError:
        # File can't be created, probably because it's a read-only file system?
        temp_file = None
    if temp_file:
        path = temp_file.temporary_file_path()
        vips_image.write_to_file(path, Q=quality)
        temp_file.size = os.path.getsize(path)  # type: ignore
        return temp_file
    # Since file couldn't be created, try to write directly to memory instead.
    vips_image = vips_image.copy_memory()
    extension = os.path.splitext(name)[1]
    buffer = vips_image.write_to_buffer(extension, Q=quality)
    return InMemoryUploadedFile(
        file=io.BytesIO(buffer),
        field_name=None,
        name=name,
        content_type=guess_type(extension)[0],
        size=len(buffer),
        charset=None,
    )


def _test():
    from pyvips import Image

    image = Image.new_from_file("example.jpg")
    print(f"Original image size: {image.width}x{image.height}")

    image = efficient_load("example.jpg", [ParsedOptions(width=100, ratio="video")])
    print(f"Efficiently loaded image size: {image.width}x{image.height}")


def _test2():
    from PIL import Image as PILImage

    image = Image.new_from_file("example.jpg")
    image = scale_image(image, (700, 500), focal_window=(0.2, 0, 0.8, 0.5))

    buffer = image.write_to_buffer(".jpg[Q=90]")

    # Convert buffer to PIL image
    pil_image = PILImage.open(io.BytesIO(buffer))
    pil_image.show()


if __name__ == "__main__":
    while True:
        _test()
