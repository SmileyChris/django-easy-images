from __future__ import absolute_import, unicode_literals
import re

from django import template
from django.utils import six
from django.utils.encoding import force_text

from easy_images.aliases import aliases
from easy_images.image import EasyImage

register = template.Library()
re_dimensions = re.compile('(\d+)[,x](\d+)$')


@register.filter
def image(source, opts):
    if not isinstance(opts, dict):
        opts = aliases.get(force_text(opts))
    if opts is None:
        return ''
    return EasyImage(source, opts)


@register.assignment_tag(takes_context=True)
def image_alias(context, alias):
    return aliases.get(force_text(alias), app_name=context.current_app)


class ImageNode(template.Node):

    def __init__(self, source, opts, as_name):
        self.source = source
        self.opts = opts
        self.as_name = as_name

    def render(self, context):
        source = self.source.resolve(context)
        opts = {}
        for key, value in six.iteritems(self.opts):
            if hasattr(value, 'resolve'):
                value = value.resolve(context)
            if value is not None and value != '':
                opts[key] = value
        image = EasyImage(source, opts)
        if self.as_name:
            context[self.as_name] = image
            return ''
        return image


def _build_opts(args, parser):
    for arg in args:
        parts = arg.split('=', 1)
        key = parts[0]
        try:
            value = parser.compile_filter(parts[1])
        except IndexError:
            value = True
        if not value:
            continue
        if isinstance(value, six.string_types):
            dimensions = re_dimensions.match(value)
            if dimensions:
                value = (int(part) for part in dimensions.groups())
        yield key, value


@register.tag(name='image')
def do_image(parser, token):
    args = token.split_contents()
    tag_name = args.pop(0)
    as_name = None
    if len(args) >= 2:
        if args[-2] == 'as':
            as_name = args[-1]
            args = args[:-2]
    if args < 2:
        raise template.TemplateSyntaxError(
            '{0} tag requires at least the source and one option'.format(
                tag_name))
    source = parser.compile_filter(args.pop(0))
    opts = dict(_build_opts(args, parser))
    return ImageNode(source, opts, as_name)
