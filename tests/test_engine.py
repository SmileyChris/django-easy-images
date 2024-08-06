import tempfile
from pathlib import Path

from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)

from easy_images.engine import efficient_load, scale_image
from easy_images.options import ParsedOptions
from pyvips import Image


def test_efficient_load():
    """
    Efficiently loaded image should be at least 3x the largest target size.
    """
    # Create a test image
    image = Image.black(1000, 1000)
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = Path(tmpdir) / "test.jpg"
        image.write_to_file(image_path)
        # Test against a few target sizes
        e_image = efficient_load(
            image_path,
            [
                ParsedOptions(width=100, ratio="video"),
                ParsedOptions(width=50, ratio="video"),
            ],
        )
        assert (e_image.width, e_image.height) == (500, 500)
        e_image = efficient_load(
            image_path,
            [
                ParsedOptions(width=30, ratio="video_vertical"),
                ParsedOptions(width=30, ratio="square"),
            ],
        )
        assert (e_image.width, e_image.height) == (250, 250)
        # Test against a percentage target size
        e_image = efficient_load(image_path, [ParsedOptions(width=10, ratio="square")])
        assert (e_image.width, e_image.height) == (125, 125)
        # Test against a large target size
        e_image = efficient_load(
            image_path, [ParsedOptions(width=5000, ratio="square")]
        )
        assert (e_image.width, e_image.height) == (1000, 1000)


def test_efficient_load_from_memory():
    image = Image.black(1000, 1000)
    file = SimpleUploadedFile("test.jpg", image.write_to_buffer(".jpg[Q=90]"))
    e_image = efficient_load(file, [ParsedOptions(width=100, ratio="video")])
    assert (e_image.width, e_image.height) == (500, 500)


def test_scale():
    source = Image.black(1000, 1000)
    scaled_cover = scale_image(source, (400, 500))
    assert (scaled_cover.width, scaled_cover.height) == (500, 500)
    scaled = scale_image(source, (400, 500), contain=True)
    assert (scaled.width, scaled.height) == (400, 400)
    cropped = scale_image(source, (400, 500), crop=True)
    assert (cropped.width, cropped.height) == (400, 500)

    small_src = Image.black(100, 100)
    cropped_upscale = scale_image(small_src, (400, 500), crop=True)
    assert (cropped_upscale.width, cropped_upscale.height) == (400, 500)

    scaled_not_upscale = scale_image(small_src, (400, 500), contain=True)
    assert (scaled_not_upscale.width, scaled_not_upscale.height) == (100, 100)
