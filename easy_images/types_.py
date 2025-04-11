from __future__ import absolute_import, annotations

import re
from typing import Literal, TypeAlias, TypedDict

CropChoices: TypeAlias = Literal[
    "center",
    "tl",
    "tr",
    "bl",
    "br",
    "t",
    "b",
    "l",
    "r",
]
WidthChoices: TypeAlias = Literal[
    "xs",
    "sm",
    "md",
    "lg",
    "screen-sm",
    "screen-md",
    "screen-lg",
    "screen-xl",
    "screen-2xl",
]
RatioChoices: TypeAlias = Literal[
    "square",
    "video",
    "video_vertical",
    "golden",
    "golden_vertical",
]

alternative_re = re.compile(r"^(\d+w|\d(?:\.\d)?x)$")

BuildChoices: TypeAlias = Literal["srcset", "src", "all", None]


class Options(TypedDict, total=False):
    quality: int
    crop: tuple[float, float] | CropChoices | bool
    contain: bool
    window: tuple[float, float, float, float] | None
    width: int | WidthChoices | None
    ratio: float | tuple[float, float] | RatioChoices | None
    # Meta options:
    alt: str | None
    width_multiplier: float
    srcset_width: int
    mimetype: str


class ImgOptions(Options, total=False):
    format: str
    densities: list[int | float]
    sizes: dict[str | int, int | str | Options]
    img_attrs: dict[str, str]
