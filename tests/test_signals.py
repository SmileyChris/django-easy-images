from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

import pyvips
from easy_images import Img
from easy_images.models import EasyImage
from easy_images.signals import queued_img
from tests.easy_images_tests.models import Profile


@pytest.mark.django_db
def test_queue():
    img = Img(width=100, densities=[])
    img.queue(Profile, fields=None)

    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=b"123")
    )

    assert EasyImage.objects.count() == 2


@pytest.mark.django_db
def test_queue_with_build_src():
    img = Img(width=100, densities=[])
    img.queue(Profile, build="src", fields=None)
    content = pyvips.Image.black(200, 200).write_to_buffer(".jpg")
    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=content)
    )

    # base jpg, avif
    assert EasyImage.objects.count() == 2
    assert EasyImage.objects.filter(image="").count() == 1


@pytest.mark.django_db
def test_queue_with_build_all():
    img = Img(width=100)
    img.queue(Profile, build="srcset", fields=None)
    content = pyvips.Image.black(200, 200).write_to_buffer(".jpg")
    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=content)
    )

    # base jpg, avif, avif 2x
    assert EasyImage.objects.count() == 3
    assert EasyImage.objects.filter(image="").count() == 0


@pytest.mark.django_db
def test_queued_img_signal():
    img = Img(width=100, densities=[])
    img.queue(Profile, fields=None)

    handler = MagicMock()
    queued_img.connect(handler)

    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=b"123")
    )
    # .queue is triggered, which triggers the queued_img signal
    assert handler.called
