import pytest

from easy_images.options import ParsedOptions


def test_parsed_options_initialization():
    options = ParsedOptions(width=100, quality=80)
    assert options.width == 100
    assert options.quality == 80


@pytest.mark.parametrize(
    "ratio, expected_size",
    [
        ("video", (100, 56)),
        ("square", (100, 100)),
        ("golden_vertical", (100, 161)),
        ("3/4", (100, 133)),
    ],
)
def test_size(ratio, expected_size):
    options = ParsedOptions(width=100, ratio=ratio)
    assert options.size == expected_size


def test_size_with_multiplier():
    options = ParsedOptions(width=100, ratio="video", width_multiplier=2)
    assert options.size == (200, 112)


@pytest.mark.parametrize(
    "croption, expected_crop",
    [
        (True, (0.5, 0.5)),
        (False, None),
        ("0.5,.5", (0.5, 0.5)),
        ("center", (0.5, 0.5)),
        ("t", (0.5, 0)),
        ("r", (1, 0.5)),
        ("bl", (0, 1)),
    ],
)
def test_crop(croption, expected_crop):
    options = ParsedOptions(crop=croption)
    assert options.crop == expected_crop


def test_hash():
    assert (
        ParsedOptions(quality=80).hash().hexdigest()
        == "cce6431a80fe3a84c7ea9f6c5293cbce4ed8848349bb0f2182eb6bb0d7a19f78"
    )


def test_str():
    assert (
        str(ParsedOptions(width=100, ratio="video"))
        == '{"crop": null, "mimetype": null, "quality": 80, "ratio": 1.7777777777777777, "width": 100, "window": null}'
    )
    assert (
        str(ParsedOptions(width=100, contain=True))
        == '{"contain": true, "crop": null, "mimetype": null, "quality": 80, "ratio": null, "width": 100, "window": null}'
    )
