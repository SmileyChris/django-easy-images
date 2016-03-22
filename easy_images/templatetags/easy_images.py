from __future__ import absolute_import, unicode_literals
import re

from django import template
from django.template.context import BaseContext
from django.utils import six
from django.utils.encoding import force_text

from easy_images.aliases import aliases
from easy_images.image import EasyImage, EasyImageBatch

register = template.Library()
re_dimensions = re.compile('(\d+)[,x](\d+)$')
CONTEXT_KEY = 'easy_image_batch'
empty_context = BaseContext()


class ImageNode(template.Node):

    def __init__(self, source_obj, opts, alias_obj, as_name):
        self.source_obj = source_obj
        self.alias_obj = alias_obj
        self.opts = opts
        self.as_name = as_name

    def render(self, context):
        source = self.source_obj.resolve(context)
        opts = {}
        if self.alias_obj:
            alias = self.alias_obj.resolve(context)
            alias_opts = aliases.get(
                force_text(alias), app_name=context.current_app)
            opts.update(alias_opts)
        for key, value in six.iteritems(self.opts):
            if hasattr(value, 'resolve'):
                value = value.resolve(context)
            if value or value == 0:
                opts[key] = value
            else:
                opts.pop(key, None)
        if opts != alias_opts:
            opts.pop('ALIAS', None)
            opts.pop('ALIAS_APP_NAME', None)
        image = EasyImage(source, opts)

        # If batch processing images, either gather it now or try to populate
        # it from the prebuilt batch.
        batch = context.render_context.get(CONTEXT_KEY)
        if batch:
            if getattr(batch, 'gathering', None):
                batch.add_image(image)
                # Set the Image meta to avoid it getting built early.
                image.meta = {}
            else:
                batch.set_meta(image)

        if self.as_name:
            context[self.as_name] = image
            return ''
        return image


def _build_opts(args, parser=None):
    for arg in args:
        parts = arg.split('=', 1)
        if len(parts) == 2:
            value = parts[1]
            if parser:
                value = parser.compile_filter(value)
            else:
                try:
                    value = template.Variable(value).resolve(empty_context)
                except template.VariableDoesNotExist:
                    # When not dealing with a parser, assume any non-literal
                    # type is a raw string.
                    value = parts[1]
        else:
            value = True
        if len(parts) == 2:
            dimensions = re_dimensions.match(parts[1])
            if dimensions:
                value = [int(part) for part in dimensions.groups()]
        yield parts[0], value


@register.tag(name='image')
def image_tag(parser, token):
    """
    Create a new image, providing image options and/or an alias.

    Format::

        {% image person.avatar crop %}
        {% image person.avatar alias 'square' %}
    """
    args = token.split_contents()
    tag_name = args.pop(0)
    as_name = None
    if args[-2] == 'as':
        as_name = args[-1]
        args = args[:-2]
    alias = None
    for i, arg in enumerate(args[:-1]):
        if arg == 'alias':
            alias = parser.compile_filter(args[i+1])
            # Remove the alias keyword and the following argument.
            del args[i:i+2]
            break
    if len(args) < 2 and not alias:
        raise template.TemplateSyntaxError(
            '{0} tag requires at least the source and one option'.format(
                tag_name))
    source = parser.compile_filter(args.pop(0))
    opts = dict(_build_opts(args, parser))
    return ImageNode(source, opts, alias, as_name)


class ImagebatchNode(template.Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        batch = context.render_context.get(CONTEXT_KEY)
        if not batch:
            batch = EasyImageBatch()
            context.render_context[CONTEXT_KEY] = batch
        rendering = getattr(batch, 'rendering', None)
        # Don't virtually render nested tags.
        if not rendering:
            batch.rendering = True
            batch.gathering = True
            # Virtually render which will populate the batch.
            self.nodelist.render(context)
            batch.gathering = False
        output = self.nodelist.render(context)
        if not rendering:
            batch.rendering = False
        return output


@register.tag
def imagebatch(parser, token):
    """
    Image tags after this tag check are virtually rendered and added to an
    EasyImageBatch dictionary on the context.

    The batch is then generated at once, and the meta dictionary for each
    EasyImage is placed in a dictionary in the render_context that the image
    tags can access during a second render.

    For example::

        {% imagebatch %}

        {% for obj in queryset %}
        <div class="gallery-item">
            <img src="{% image obj.photo 'gallery-square' %}" alt="{{ obj }}">
        </div>
        {% endfor %}
    """
    nodelist = parser.parse()
    return ImagebatchNode(nodelist)
