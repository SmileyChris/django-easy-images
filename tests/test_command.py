from io import StringIO
from unittest import mock

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.management import call_command
from django.test import override_settings

from easy_images.engine import vips_to_django
from easy_images.models import EasyImage, ImageStatus, get_storage_name
from pyvips import Image


@pytest.mark.django_db
def test_empty():
    test_output = StringIO()
    call_command("build_img_queue", stdout=test_output)
    assert test_output.getvalue() == (
        """Building queued <img> thumbnails...
No <img> thumbnails required building
"""
    )


@pytest.mark.django_db
def test_queue():
    EasyImage.objects.create(args={}, name="1")
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="3")
    EasyImage.objects.create(status=ImageStatus.BUILD_ERROR, args={}, name="4")
    EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, args={}, name="5")
    for name in "678":
        EasyImage.objects.create(
            image="test",
            status=ImageStatus.BUILT,
            width=800,
            height=600,
            args={},
            name=name,
        )
    EasyImage.objects.create(args={}, name="2")
    test_output = StringIO()
    with mock.patch("easy_images.models.EasyImage.build", return_value=True):
        call_command("build_img_queue", stdout=test_output)
    assert test_output.getvalue() == (
        """Building queued <img> thumbnails...
Skipping 1 marked as already building...
Skipping 1 with source errors...
Skipping 1 with build errors...
Built 2 <img> thumbnails
"""
    )


@pytest.mark.django_db
def test_retry():
    EasyImage.objects.create(args={}, name="1")
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="2")
    EasyImage.objects.create(
        status=ImageStatus.BUILD_ERROR, args={}, name="3", error_count=1
    )
    EasyImage.objects.create(
        status=ImageStatus.SOURCE_ERROR, args={}, name="4", error_count=2
    )
    for name in "567":
        EasyImage.objects.create(
            image="test",
            status=ImageStatus.BUILT,
            width=800,
            height=600,
            args={},
            name=name,
        )
    test_output = StringIO()
    with mock.patch("easy_images.models.EasyImage.build", return_value=True):
        call_command("build_img_queue", stdout=test_output, retry=1)
    assert test_output.getvalue() == (
        """Building queued <img> thumbnails...
Skipping 1 marked as already building...
Retrying 0 with source errors (1 with more than 1 retries skipped)...
Retrying 1 with build errors...
Built 2 <img> thumbnails
"""
    )


@pytest.mark.django_db
def test_force():
    EasyImage.objects.create(args={}, name="1")
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="2")
    EasyImage.objects.create(status=ImageStatus.BUILD_ERROR, args={}, name="3")
    EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, args={}, name="4")
    for name in "567":
        EasyImage.objects.create(
            image="test",
            status=ImageStatus.BUILT,
            width=800,
            height=600,
            args={},
            name=name,
        )
    test_output = StringIO()
    with mock.patch("easy_images.models.EasyImage.build", return_value=True):
        call_command("build_img_queue", stdout=test_output, force=True)
    assert test_output.getvalue() == (
        """Building queued <img> thumbnails...
Built 4 <img> thumbnails
"""
    )


def _create_easyimage():
    image = Image.black(1000, 1000)
    file = vips_to_django(image, "test.jpg")
    name = default_storage.save("test.jpg", file)
    img = EasyImage.objects.create(
        storage=get_storage_name(default_storage),
        name=name,
        args={"width": 200, "ratio": 1},
    )
    return img, file


@pytest.mark.django_db
def test_build():
    img, file = _create_easyimage()
    assert isinstance(file, TemporaryUploadedFile)
    file.close()
    img.build()
    assert img.image
    assert (img.width, img.height) == (200, 200)


@pytest.mark.django_db
@override_settings(FILE_UPLOAD_TEMP_DIR="/")
def test_build_via_memory():
    img, file = _create_easyimage()
    assert isinstance(file, InMemoryUploadedFile)
    img.build()
    assert img.image
    assert (img.width, img.height) == (200, 200)
