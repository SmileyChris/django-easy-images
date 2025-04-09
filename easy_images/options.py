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

width_options: dict[str, int] = {
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
    __slots__ = (
        "quality",
        "crop",
        "contain",
        "window",
        "width",
        "ratio",
        "mimetype",
    )

    quality: int
    crop: tuple[float, float] | None
    contain: bool
    window: tuple[float, float, float, float] | None
    width: int | None
    ratio: float | None
    mimetype: str | None

    _defaults = {"contain": False}

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
        # Process known slots first
        processed_keys = set()
        for key in self.__slots__:
            processed_keys.add(key)
            if key in options and options[key] is not None:
                value = options[key]
                if isinstance(value, Variable):
                    # Resolve Django template variables if present
                    value = value.resolve(context)
                parse_func = getattr(self, f"parse_{key}")
                # Pass all options in case parse funcs need context (like width_multiplier)
                value = parse_func(value, **options)
            elif key in self._defaults:
                value = self._defaults[key]
            else:
                # Set default quality, others default to None implicitly via type hints
                value = 80 if key == "quality" else None
            setattr(self, key, value)

        # ParsedOptions only processes keys in its __slots__.
        # It does not validate or care about other keys passed in **options.
        # Validation of allowed keys for a specific context (like a template tag)
        # should happen in the calling code.

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
    def parse_crop(value, **options) -> tuple[float, float] | None:
        if not value:
            return None
        if value is True:
            return (0.5, 0.5)
        try:
            # Check if value is a key in crop_options (requires hashable value)
            if value in crop_options:
                return crop_options[value]
        except TypeError:
            # value is not hashable (e.g., a list), proceed to other checks
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
    def parse_contain(value, **options) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            val = value.lower()
            if val in ("true", "1", "yes"):
                return True
            if val in ("false", "0", "no"):
                return False
        # Allow integer 1 or 0
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        raise ValueError(f"Invalid contain value {value}")

    @staticmethod
    def parse_window(value, **options) -> tuple[float, float, float, float] | None:
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
    def parse_width(value, **options) -> int | None:
        if value is None:
            return None
        try:
            # Check if value is a key in width_options (requires hashable value)
            if value in width_options:
                value = width_options[value]
        except TypeError:
            # value is not hashable (e.g., a list), proceed to other checks
            pass
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid width value {value}")
        # Ensure value is an integer before applying multiplier
        current_width = value

        if multiplier_val := options.get("width_multiplier"):
            try:
                multiplier = float(multiplier_val)
                current_width = int(current_width * multiplier)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid width multiplier value {multiplier_val}")
        return current_width

    @staticmethod
    def parse_ratio(value, **options) -> float | None:
        if value is None:
            return None
        try:
            # Check if value is a key in ratio_options (requires hashable value)
            if value in ratio_options:
                return ratio_options[value]
        except TypeError:
            # value is not hashable (e.g., a list), proceed to other checks
            pass
        if isinstance(value, str):
            value = value.split("/")
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                return float(value[0]) / float(value[1])
            except (ValueError, TypeError):
                pass
        # At this point, value could be a single number (int/float)
        # or a string representation of a number, or potentially
        # a list/tuple that wasn't handled above (which is invalid).
        try:
            # Attempt direct conversion if it's not a list/tuple already handled
            if not isinstance(value, (list, tuple)):
                return float(value)
        except (ValueError, TypeError):
            # If conversion fails, fall through to the exception
            pass
        # If we reach here, the value was invalid
        raise ValueError(f"Invalid ratio value {value}")

    @staticmethod
    def parse_mimetype(value, **options) -> str | None:
        if value is None:
            return None
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
        return {
            key: getattr(self, key)
            for key in self.__slots__
            if key not in self._defaults or getattr(self, key) != self._defaults[key]
        }

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
