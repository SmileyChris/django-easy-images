import json
from hashlib import sha256
from typing import cast

from django.template import Context, Variable
from django.utils.text import smart_split

crop_options: dict[str, tuple[float, float]] = {
    "center": (0.5, 0.5),
    "tl": (0, 0),
    "tr": (1, 0),
    "bl": (0, 1),
    "br": (1, 1),
    "t": (0.5, 0),
    "b": (0.5, 1),
    "l": (0, 0.5),
    "r": (1, 0.5),
}

width_options = {
    "xs": 320,
    "sm": 384,
    "md": 448,
    "lg": 512,
    "screen-sm": 640,
    "screen-md": 768,
    "screen-lg": 1024,
    "screen-xl": 1280,
    "screen-2xl": 1536,
}

ratio_options: dict[str, float] = {
    "square": 1,
    "video": 16 / 9,
    "video_vertical": 9 / 16,
    "golden": 1.618033988749895,
    "golden_vertical": 1 / 1.618033988749895,
}


class ParsedOptions:
    __slots__ = ("quality", "crop", "window", "width", "ratio", "mimetype")

    quality: int
    crop: tuple[float, float] | None
    window: tuple[float, float, float, float] | None
    width: int | None
    ratio: float | None
    mimetype: str | None

    def __init__(self, bound=None, string="", /, **options):
        if string:
            for part in smart_split(string):
                key, value = part.split("=", 1)
                if key not in options:
                    options[key] = Variable(value)
        context = Context()
        if bound:
            for key, value in bound.__dict__.items():
                context[key] = value
        for key in self.__slots__:
            value = options.get(key)
            if isinstance(value, Variable):
                value = value.resolve(context)
            if value and value != 0:
                parse_func = getattr(self, f"parse_{key}")
                setattr(self, key, parse_func(value, **options))
            else:
                setattr(self, key, 80 if key == "quality" else None)

    @classmethod
    def from_str(cls, s: str):
        str_options: dict[str, str] = {}
        for part in s.split(" "):
            key, value = part.split("=", 1)
            str_options[key] = value
        return cls(**str_options)

    @staticmethod
    def parse_quality(value, **options) -> int:
        if not value:
            return 80
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid quality value {value}")

    @staticmethod
    def parse_crop(value, **options) -> tuple[float, float]:
        if value is True:
            return (0.5, 0.5)
        try:
            if value in crop_options:
                return crop_options[value]
        except TypeError:
            pass
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                return cast(tuple[float, float], tuple(float(n) for n in value))
            except (ValueError, TypeError):
                pass
        raise ValueError(f"Invalid crop value {value}")

    @staticmethod
    def parse_window(value, **options) -> tuple[float, float, float, float]:
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, (tuple, list)) and len(value) == 4:
            try:
                return cast(
                    tuple[float, float, float, float], tuple(float(n) for n in value)
                )
            except (ValueError, TypeError):
                pass
        raise ValueError(f"Invalid window value {value}")

    @staticmethod
    def parse_width(value, **options) -> int:
        if value in width_options:
            value = width_options[value]
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid width value {value}")
        if multiplier := options.get("width_multiplier"):
            try:
                value = int(value * multiplier)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid width multiplier value {multiplier}")
        return value

    @staticmethod
    def parse_ratio(value, **options) -> float:
        if value in ratio_options:
            return ratio_options[value]
        if isinstance(value, str):
            value = value.split("/")
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                return float(value[0]) / float(value[1])
            except (ValueError, TypeError):
                pass
        try:
            if isinstance(value, list):
                value = value[0]
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid ratio value {value}")

    @staticmethod
    def parse_mimetype(value, **options) -> str:
        return str(value)

    def __str__(self):
        return json.dumps(self.to_dict(), sort_keys=True)

    def hash(self):
        return sha256(str(self).encode(), usedforsecurity=False)

    @property
    def size(self):
        if not self.width or not self.ratio:
            return None
        return self.width, int(self.width / self.ratio)

    def to_dict(self):
        return {key: getattr(self, key) for key in self.__slots__}

    def source_x(self, source_x: int):
        if self.window:
            return int(self.window[2] * source_x) - int(self.window[0] * source_x)
        return self.width or 0

    def source_y(self, source_y: int):
        if self.window:
            return int(self.window[3] * source_y) - int(self.window[1] * source_y)
        if not self.width or not self.ratio:
            return 0
        return int(self.width / self.ratio)
