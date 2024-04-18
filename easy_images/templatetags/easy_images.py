from typing import cast

from django import template
from django.template.base import token_kwargs

from easy_images.core import Img
from easy_images.options import ParsedOptions
from easy_images.types import ImgOptions

register = template.Library()


class ImgNode(template.Node):
    def __init__(self, file, img_instance, options, as_var):
        self.file = file
        self.img_instance = img_instance
        self.options = options
        self.as_var = as_var

    def render(self, context):
        file = self.file.resolve(context)
        resolved_options = {key: value.resolve(context) for key, value in self.options}
        base_opts = ParsedOptions(**resolved_options)
        options = cast(
            ImgOptions,
            {
                key: getattr(base_opts, key)
                for key in ParsedOptions.__slots__
                if getattr(base_opts, key) is not None
            },
        )
        img_attrs = {}
        for key, value in resolved_options.items():
            if key.startswith("img_"):
                img_attrs[key[4:]] = value
            elif key == "densities":
                options["densities"] = (
                    [float(d) for d in value.split(",")]
                    if isinstance(value, str)
                    else value
                )
            elif key == "size":
                if not isinstance(value, str) or "," not in value:
                    raise ValueError(
                        "size must be a string with a comma between the media and size"
                    )
                sizes = options.setdefault("sizes", {})
                size_key, value = value.split(",")
                if size_key.isdigit():
                    size_key = int(size_key)
                sizes[size_key] = int(value)
            elif key == "format":
                options["format"] = value
            else:
                raise ValueError(f"Invalid option {key}")
        options["img_attrs"] = img_attrs
        output = Img(**options)(file, alt=resolved_options["alt"]).as_html()
        if self.as_var:
            context[self.as_var] = output
            return ""
        return output


@register.tag
def img(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise template.TemplateSyntaxError(f"{bits[0]} tag requires a field file")
    file = parser.compile_filter(bits[1])
    if len(bits) < 3:
        raise template.TemplateSyntaxError(
            f"{bits[0]} tag requires an Img instance or options"
        )
    options = bits[2:]
    if "=" not in options[0]:
        img_instance = parser.compile_filter(options[0])
        options = options[1:]
    as_var = None
    if len(options) > 1 and options[-2] == "as":
        as_var = options[-1]
        options = options[:-2]
    options = token_kwargs(options, parser)
    if "alt" not in options:
        raise template.TemplateSyntaxError(f"{bits[0]} tag requires an alt attribute")

    return ImgNode(file, img_instance, options, as_var)
