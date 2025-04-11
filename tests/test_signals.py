import uuid
from typing import Iterator
from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest import FixtureRequest  # Import from public API

import pyvips
from easy_images import Img
from easy_images.models import EasyImage
from easy_images.signals import (
    file_post_save,
    queued_img,
)
from easy_images.types_ import (
    BuildChoices,
    ImgOptions,
)
from tests.easy_images_tests.models import Profile


@pytest.fixture
def profile_queue_img(request: FixtureRequest) -> Iterator[Img]:
    """
    Fixture to set up and tear down the Img.queue signal connection for Profile model.
    Handles different build options via indirect parametrization if needed,
    or can be used directly for default setup.
    """
    # Get build option if parametrized
    build_option: BuildChoices | None = getattr(request, "param", None)

    # Define standard Img options used across tests
    # test_queue and test_queued_img_signal use densities=[]
    # test_queue_with_build_src uses densities=[]
    # test_queue_with_build_srcset uses default densities
    img_options: ImgOptions = {"width": 100}
    if build_option is None or build_option == "src":
        # Ensure the key exists before assigning, although ImgOptions allows partials
        img_options["densities"] = []

    # Unpack the TypedDict directly
    img = Img(**img_options)

    # Generate a unique ID for this specific handler connection
    handler_uid = f"test_handler_{uuid.uuid4().hex}"

    # Connect the signal handler using the unique ID
    # This requires Img.queue to accept dispatch_uid (added in previous step)
    img.queue(Profile, build=build_option, fields=None, dispatch_uid=handler_uid)

    yield img  # Provide the configured Img instance to the test

    # Teardown: Disconnect the specific handler using its unique ID
    disconnected = file_post_save.disconnect(dispatch_uid=handler_uid, sender=Profile)
    assert disconnected, f"Failed to disconnect signal handler with UID {handler_uid}"


@pytest.mark.django_db
def test_queue(profile_queue_img):
    """Test that the queue mechanism triggers the signal without building."""
    # img and queue setup is handled by the fixture

    handler = MagicMock()
    queued_img.connect(handler)

    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=b"123")
    )

    # Assert the signal was called, indicating queuing happened
    assert handler.called
    # Assert no objects were actually created in DB yet due to lazy loading
    assert EasyImage.objects.count() == 0


@pytest.mark.parametrize("profile_queue_img", ["src"], indirect=True)
@pytest.mark.django_db
def test_queue_with_build_src(profile_queue_img):
    """Test queuing with immediate build of source (base) image."""
    # img and queue setup is handled by the fixture
    content = pyvips.Image.black(200, 200).write_to_buffer(".jpg")
    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=content)
    )

    # Only the base image record should be created and built
    assert EasyImage.objects.count() == 1
    assert EasyImage.objects.filter(image="").count() == 0  # Base image should be built


@pytest.mark.parametrize("profile_queue_img", ["srcset"], indirect=True)
@pytest.mark.django_db
def test_queue_with_build_srcset(profile_queue_img):
    """Test queuing with immediate build of srcset images only."""
    # img (with default densities) and queue setup is handled by the fixture
    content = pyvips.Image.black(200, 200).write_to_buffer(".jpg")

    # Get PKs before creation
    pks_before = set(EasyImage.objects.values_list("pk", flat=True))

    # Create profile, triggering signal and build="srcset"
    profile = Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=content)
    )

    # Get PKs after creation
    pks_after = set(EasyImage.objects.values_list("pk", flat=True))
    new_pks = pks_after - pks_before

    # Assert 3 new EasyImage objects were created (base, webp 1x, webp 2x)
    assert len(new_pks) == 3, f"Expected 3 new EasyImages, found {len(new_pks)}"

    # Find the base PK among the newly created ones
    bound_img = profile_queue_img(profile.image)  # Get BoundImg to access _base_pk
    base_pk = bound_img._parent_batch._requests[bound_img._request_id]["base_pk"]
    assert base_pk in new_pks, "Base PK not found among newly created PKs"

    # Assert only the base image among the new ones is unbuilt
    unbuilt_new_images = EasyImage.objects.filter(pk__in=new_pks, image="")
    assert unbuilt_new_images.count() == 1, "Expected 1 unbuilt new image"
    unbuilt_first = unbuilt_new_images.first()
    assert unbuilt_first is not None, "QuerySet returned None unexpectedly"
    assert unbuilt_first.pk == base_pk, "The unbuilt image was not the base image"


@pytest.mark.django_db
def test_queued_img_signal(profile_queue_img):
    """Test the queued_img signal is dispatched correctly when needed."""
    # img and queue setup is handled by the fixture

    handler = MagicMock()
    queued_img.connect(handler)

    Profile.objects.create(
        name="Test", image=SimpleUploadedFile(name="test.jpg", content=b"123")
    )
    # .queue is triggered, which triggers the queued_img signal
    assert handler.called
