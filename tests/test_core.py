from unittest.mock import MagicMock, Mock, patch  # Import Mock

import pytest
from django.db.models import FileField
from django.db.models.fields.files import FieldFile

from easy_images.core import ImageBatch, Img  # Import ImageBatch
from easy_images.models import EasyImage


# Remove patch decorator - mock storage inside test
@pytest.mark.django_db
@patch("easy_images.models.get_storage_name", return_value="default")
def test_as_html_fallback(mock_get_storage):
    """Test HTML generation before loading/building (uses fallback URL)."""
    # Create mock storage and assign URL
    mock_storage = Mock()
    mock_storage.url.return_value = "/test.jpg"

    generator = Img(width=100)
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    source.storage = mock_storage  # Assign mock storage to instance
    # Expect src attribute because base_url falls back to source.url
    assert generator(source).as_html() == '<img src="/test.jpg" alt="">'


@pytest.mark.django_db  # Add DB access mark
@patch.object(ImageBatch, "get_image")  # Mock get_image
@patch.object(ImageBatch, "_ensure_loaded", return_value=None)  # Mock _ensure_loaded
def test_as_html_loaded(mock_ensure_loaded, mock_get_image):
    """Test HTML generation after images are theoretically loaded."""
    # --- Setup Mocks ---
    # Mock EasyImage instances
    mock_base = MagicMock(spec=EasyImage)
    mock_base.image.url = "/img/base.jpg"
    mock_base.width = 100
    mock_base.height = 56  # Assuming 16:9 ratio for width 100

    mock_srcset1 = MagicMock(spec=EasyImage)
    mock_srcset1.image.url = "/img/srcset1.webp"
    mock_srcset1.width = 100  # Assuming 1x density
    mock_srcset1.height = 56

    mock_srcset2 = MagicMock(spec=EasyImage)
    mock_srcset2.image.url = "/img/srcset2.webp"
    mock_srcset2.width = 200  # Assuming 2x density
    mock_srcset2.height = 112

    # --- Test Logic ---
    generator = Img(
        width=100, format="webp", densities=[1, 2]
    )  # Use densities for simpler srcset
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    # No need to mock source.url here as get_image is mocked

    bound_img = generator(source)
    # Manually set the _requests data for the mock, as add() wasn't fully run
    # This is a simplification for the test.
    dummy_base_pk = "00000000-0000-0000-0000-000000000001"
    dummy_srcset1_pk = "00000000-0000-0000-0000-000000000002"
    dummy_srcset2_pk = "00000000-0000-0000-0000-000000000003"
    bound_img._parent_batch._requests[bound_img._request_id] = {
        "base_pk": dummy_base_pk,
        "srcset_pks": [dummy_srcset1_pk, dummy_srcset2_pk],
        "srcset_pk_options": {  # Need this for srcset generation in as_html
            dummy_srcset1_pk: {"srcset_width": 100},
            dummy_srcset2_pk: {"srcset_width": 200},
        },
        "alt": "",  # Default alt
        "sizes_attr": "",  # No sizes defined
        "source_name_fallback": "test.jpg",
        "storage_name": "default",  # Assume default storage
    }

    # Configure the mock to return mocks based on these dummy PKs
    def get_image_side_effect(pk):
        if pk == dummy_base_pk:
            return mock_base
        if pk == dummy_srcset1_pk:
            return mock_srcset1
        if pk == dummy_srcset2_pk:
            return mock_srcset2
        return None

    mock_get_image.side_effect = get_image_side_effect

    html_output = bound_img.as_html()

    # --- Assertions ---
    mock_ensure_loaded.assert_called()  # Ensure loading was triggered at least once
    assert mock_get_image.call_count >= 3  # Base + 2 srcset items

    # Check the generated HTML
    assert 'src="/img/base.jpg"' in html_output
    assert 'alt=""' in html_output
    assert 'srcset="' in html_output
    # Order in srcset might vary, check parts
    assert "/img/srcset1.webp 100w" in html_output
    assert "/img/srcset2.webp 200w" in html_output
    assert 'width="100"' in html_output
    assert 'height="56"' in html_output


# Remove patch decorator - mock storage inside test
@pytest.mark.django_db
@patch("easy_images.models.get_storage_name", return_value="default")
def test_sizes_fallback(mock_get_storage):
    """Test sizes attribute generation before loading."""
    # Create mock storage and assign URL
    mock_storage = Mock()
    mock_storage.url.return_value = "/test.jpg"

    generator = Img(width=200, sizes={800: 100})
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    source.storage = mock_storage  # Assign mock storage to instance
    # Expect src (fallback) and sizes attributes
    assert (
        generator(source).as_html()
        == '<img src="/test.jpg" alt="" sizes="(max-width: 800px) 100px, 200px">'
    )


@pytest.mark.django_db  # Add DB access mark
@patch.object(ImageBatch, "get_image")  # Mock get_image
@patch.object(ImageBatch, "_ensure_loaded", return_value=None)  # Mock _ensure_loaded
def test_sizes_loaded(mock_ensure_loaded, mock_get_image):
    """Test HTML generation with sizes after images are theoretically loaded."""
    # --- Setup Mocks ---
    mock_base = MagicMock(spec=EasyImage)
    mock_base.image.url = "/img/base_200.jpg"
    mock_base.width = 200
    mock_base.height = 112  # 16:9

    mock_size100 = MagicMock(spec=EasyImage)
    mock_size100.image.url = "/img/size_100.webp"
    mock_size100.width = 100
    mock_size100.height = 56

    mock_size200 = MagicMock(spec=EasyImage)
    mock_size200.image.url = "/img/size_200.webp"
    mock_size200.width = 200
    mock_size200.height = 112

    mock_size400 = MagicMock(spec=EasyImage)  # For 2x density of max width (200)
    mock_size400.image.url = "/img/size_400.webp"
    mock_size400.width = 400
    mock_size400.height = 225

    # --- Test Logic ---
    generator = Img(width=200, sizes={800: 100})  # Default densities=[2], format='webp'
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    # No need to mock source.url here

    bound_img = generator(source)
    # Manually set the _requests data for the mock
    dummy_base_pk = "10000000-0000-0000-0000-000000000001"
    dummy_size100_pk = "10000000-0000-0000-0000-000000000002"
    dummy_size200_pk = "10000000-0000-0000-0000-000000000003"  # Default size
    dummy_size400_pk = "10000000-0000-0000-0000-000000000004"  # High density
    bound_img._parent_batch._requests[bound_img._request_id] = {
        "base_pk": dummy_base_pk,
        "srcset_pks": [dummy_size100_pk, dummy_size200_pk, dummy_size400_pk],
        "srcset_pk_options": {
            dummy_size100_pk: {"srcset_width": 100},
            dummy_size200_pk: {"srcset_width": 200},
            dummy_size400_pk: {"srcset_width": 400, "width_multiplier": 2.0},
        },
        "alt": "",
        "sizes_attr": "(max-width: 800px) 100px, 200px",
        "source_name_fallback": "test.jpg",
        "storage_name": "default",
    }

    # Configure mock side effect
    def get_image_side_effect_sizes(pk):
        if pk == dummy_base_pk:
            return mock_base
        if pk == dummy_size100_pk:
            return mock_size100
        if pk == dummy_size200_pk:
            return mock_size200
        if pk == dummy_size400_pk:
            return mock_size400
        return None

    mock_get_image.side_effect = get_image_side_effect_sizes

    html_output = bound_img.as_html()

    # --- Assertions ---
    mock_ensure_loaded.assert_called()  # Ensure loading was triggered at least once
    assert mock_get_image.call_count >= 4  # Base + 3 srcset images

    assert 'src="/img/base_200.jpg"' in html_output
    assert 'alt=""' in html_output
    assert 'sizes="(max-width: 800px) 100px, 200px"' in html_output
    assert 'srcset="' in html_output
    # Check srcset parts (order might vary)
    assert "/img/size_100.webp 100w" in html_output
    assert "/img/size_200.webp 200w" in html_output
    assert "/img/size_400.webp 400w" in html_output  # High density based on max width
    assert 'width="200"' in html_output
    assert 'height="112"' in html_output
