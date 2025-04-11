from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from easy_images.core import Img
from easy_images.models import (
    EasyImage,
    ImageStatus,
    get_storage_name,
    pick_image_storage,
)
from pyvips.vimage import Image
from tests.easy_images_tests.models import Profile

thumbnail = Img(width=200, format="jpg")


@pytest.mark.django_db
def test_build_bad_source():
    storage = pick_image_storage()
    name = storage.save("bad_source.jpg", BytesIO(b"bad image data"))
    storage_name = get_storage_name(storage)
    image = EasyImage.objects.create(
        args={"width": 100}, name=name, storage=storage_name
    )
    assert image.status == ImageStatus.QUEUED
    image.build()
    assert image.status == ImageStatus.SOURCE_ERROR
    assert not image.image
    assert image.error_count == 1


@pytest.mark.django_db
def test_build_no_source():
    storage = pick_image_storage()
    storage_name = get_storage_name(storage)
    image = EasyImage.objects.create(
        args={"width": 100}, name="notafile.jpg", storage=storage_name
    )
    assert image.status == ImageStatus.QUEUED
    image.build()
    assert image.status == ImageStatus.SOURCE_ERROR
    assert image.error_count == 1


@pytest.mark.django_db
def test_build_from_filefield():
    image = Image.black(1000, 1000)
    file = SimpleUploadedFile("test.png", image.write_to_buffer(".png[Q=90]"))
    profile = Profile.objects.create(name="Test", image=file)

    thumb = thumbnail(profile.image)
    assert thumb.base_url() == "/profile-images/test.png"
    assert thumb.as_html() == '<img src="/profile-images/test.png" alt="">'


@pytest.mark.django_db
def test_build_from_filefield_with_build():
    image = Image.black(1000, 1000)
    file = SimpleUploadedFile("test.png", image.write_to_buffer(".png[Q=90]"))
    profile = Profile.objects.create(name="Test", image=file)

    thumb = thumbnail(profile.image, build="src")
    assert thumb.base_url().endswith(".png")
    assert thumb.as_html() == f'<img src="{thumb.base_url()}" alt="">'
