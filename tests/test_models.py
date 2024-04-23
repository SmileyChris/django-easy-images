from io import BytesIO

import pytest

from easy_images.models import (
    EasyImage,
    ImageStatus,
    get_storage_name,
    pick_image_storage,
)


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
