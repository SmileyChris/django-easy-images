from typing import Protocol, cast  # Import Protocol and Any

from django import template
from django.db.models.fields.files import FieldFile  # Import FieldFile for type hint
from django.template.base import token_kwargs

from easy_images.core import BoundImg, Img
from easy_images.options import ParsedOptions
from easy_images.types_ import ImgOptions


# Define a Protocol for the expected callable object (Img instance)
class ImgRendererProtocol(Protocol):
    def __call__(self, source: FieldFile, *, alt: str | None = None) -> BoundImg: ...


register = template.Library()


class ImgNode(template.Node):
    def __init__(self, file, img_instance, options, as_var):
        self.file = file
        self.img_instance = img_instance
        self.options = options
        self.as_var = as_var

    def render(self, context):
        file = self.file.resolve(context)
        resolved_options = {
            key: value.resolve(context) for key, value in self.options.items()
        }

        # --- Validate all provided options ---
        all_input_keys = set(resolved_options.keys())
        valid_parsed_options_keys = set(ParsedOptions.__slots__)
        tag_specific_keys = {
            "alt",
            "densities",
            "size",
            "format",
        }  # Keys handled directly by the tag logic
        # token_kwargs converts hyphens to underscores, so check for 'img_'
        img_attr_keys = {k for k in all_input_keys if k.startswith("img_")}

        # Combine all known/valid keys
        known_keys = valid_parsed_options_keys | tag_specific_keys | img_attr_keys

        unknown_keys = all_input_keys - known_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown options passed to 'img' tag: {', '.join(sorted(list(unknown_keys)))}"
            )

        # --- Process Valid Options ---
        # Filter options intended for ParsedOptions
        options_for_parsed = {
            k: v for k, v in resolved_options.items() if k in valid_parsed_options_keys
        }

        # Parse only the relevant options using ParsedOptions
        base_opts = ParsedOptions(**options_for_parsed)

        # Initialize the final options dict from all non-None slots in base_opts
        # This ensures defaults (like quality=80) and parsed values (like width=50) are included.
        options = cast(
            ImgOptions,
            {
                key: getattr(base_opts, key)
                for key in ParsedOptions.__slots__
                if getattr(base_opts, key) is not None
            },
        )

        # Collect img_ attributes separately first
        img_attrs = {}
        for key, value in resolved_options.items():
            # Handle keys starting with 'img_' (underscore)
            if key.startswith("img_"):
                # Convert underscore to hyphen for HTML attribute name
                attr_name = key[4:].replace("_", "-")
                # Ensure value is a string for consistency in HTML attributes
                img_attrs[attr_name] = str(value)

        # Handle special overrides for options already processed by ParsedOptions
        if "densities" in resolved_options:
            value = resolved_options["densities"]
            options["densities"] = (
                [float(d) for d in value.split(",")]
                if isinstance(value, str)
                else value
            )
        if "size" in resolved_options:
            value = resolved_options["size"]
            if not isinstance(value, str) or "," not in value:
                raise ValueError(
                    "size must be a string with a comma between the media and size"
                )
            sizes = {}
            size_key, size_value = value.split(",")
            if size_key.isdigit():
                size_key = int(size_key)
            sizes[size_key] = int(size_value)
            options["sizes"] = sizes  # Overwrite sizes dict
        if "format" in resolved_options:
            options["format"] = resolved_options["format"]  # Override format

        # Assign the collected img_attrs
        # Note: ParsedOptions doesn't handle img_attrs, so no merging needed.
        options["img_attrs"] = img_attrs

        # Resolve the optional Img instance from context
        img_renderer_resolved: object | None = None
        # Use the Protocol for type hinting
        img_renderer: ImgRendererProtocol | None = None
        if self.img_instance:
            img_renderer_resolved = self.img_instance.resolve(context)
            if not callable(img_renderer_resolved):
                raise ValueError(
                    f"The provided img_instance '{self.img_instance.var}' did not resolve to a callable object."
                )
            # Cast the resolved callable object to the Protocol
            img_renderer = cast(ImgRendererProtocol, img_renderer_resolved)

        # Use provided instance or create a new one
        if img_renderer:
            # When using a pre-configured instance, we pass the file and alt,
            # but don't override its existing options with the ones from the tag.
            # The user is expected to configure the instance beforehand.
            # We do pass the img_attrs collected from the tag though.
            # Use .get() for alt as validation happens before this point
            alt_text = resolved_options.get("alt", "")
            # Call with positional file and keyword alt, no img_attrs
            bound_image_from_instance: BoundImg = img_renderer(file, alt=alt_text)
            output = bound_image_from_instance.as_html()
        else:
            # Explicitly type hint the result of the call to Img(...)
            alt_text = resolved_options.get("alt", "")  # Use .get() for safety

            bound_image: BoundImg = Img(**options)(file, alt=alt_text)
            output = bound_image.as_html()

        if self.as_var:
            context[self.as_var] = output
            return ""  # Return empty string when using 'as var'
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
    img_instance = None
    if options and "=" not in options[0]:
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
