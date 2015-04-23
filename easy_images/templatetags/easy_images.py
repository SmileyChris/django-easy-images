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


def _populate_from_context(image, context):
    if not context:
        return
    batch = context.render_context.get(CONTEXT_KEY)
    if batch:
        if getattr(batch, 'gathering', None):
            batch.add_image(image)
            return ''
        batch.set_meta(image)


@register.filter
def image(source, opts):
    if not isinstance(opts, dict):
        opts = aliases.get(force_text(opts))
    if opts is None:
        return ''
    image = EasyImage(source, opts)
    _populate_from_context(image, get_filter_context())
    return image


@register.filter
def imageopts(image, extra_opts):
    """
    Create a new ``EasyImage`` based on an existing instance but with
    additional options.

    For example, make a greyscale version of a standard alias::

        {{ person.photo|image:"square"|imageopts:"bw" }}

    Or provide separate images for multiple pixel densities::

        {% with image=person.photo|image %}
        <img
          src="{{ image }}"
          srcset="{{ image|imageopts:"HIGHRES=1.5" }} 1.5x,
                  {{ image|imageopts:"HIGHRES=2" }} 2x"
          alt="">
        {% endwith %}
    """
    token = template.base.Token(
        token_type=template.base.TOKEN_BLOCK, contents=extra_opts)
    args = token.split_contents()
    opts = image.opts.copy()
    opts.update(_build_opts(args))
    return EasyImage(source=image.source, opts=opts)


@register.assignment_tag(takes_context=True)
def image_alias(context, alias):
    return aliases.get(force_text(alias), app_name=context.current_app)


class ImageNode(template.Node):

    def __init__(self, source_obj, opts, as_name):
        self.source_obj = source_obj
        self.opts = opts
        self.as_name = as_name

    def render(self, context):
        source = self.source_obj.resolve(context)
        opts = {}
        for key, value in six.iteritems(self.opts):
            if hasattr(value, 'resolve'):
                value = value.resolve(context)
            if value is not None and value != '':
                opts[key] = value
        image = EasyImage(source, opts)
        _populate_from_context(image, context)
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
                value = template.Variable(value).resolve(empty_context)
            try:
                resolved_value = value.resolve(empty_context)
            except template.VariableDoesNotExist:
                if parser:
                    resolved_value = None
                else:
                    # When not dealing with a parser, assume any non-literal
                    # type is a raw string.
                    resolved_value = parts[0]
            if not parser:
                # When not dealing with a parser, always just return the resolved
                value = resolved_value
        else:
            value = resolved_value = True
        if not value:
            continue
        if isinstance(resolved_value, six.string_types):
            dimensions = re_dimensions.match(resolved_value)
            if dimensions:
                value = [int(part) for part in dimensions.groups()]
        yield parts[0], value


@register.tag(name='image')
def image_tag(parser, token):
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


def get_filter_context(max_depth=4):
    """
    A simple (and perhaps dangerous) way of obtaining a context.  Keep in mind
    these shortcomings:

    1. There is no guarantee this returns the right 'context'.

    2. This only works during render execution.  So, be sure your filter
       continues to work in other cases.

    This approach uses the 'inspect' standard Python Library to harvest the
    context from the call stack.
    """
    import inspect
    stack = inspect.stack()[2:max_depth]
    for frame_info in stack:
        frame = frame_info[0]
        arg_info = inspect.getargvalues(frame)
        context = arg_info.locals.get('context')
        if context:
            return context
    return {}


class ImagebatchNode(template.Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        batch = context.render_context.get(CONTEXT_KEY)
        if not batch:
            batch = EasyImageBatch()
            context.render_context[CONTEXT_KEY] = batch
        gathering = getattr(batch, 'gathering', None)
        if not gathering:
            batch.gathering = True
        self.nodelist.render(context)
        if not gathering:
            batch.gathering = False
        return ''


@register.tag
def imagebatch(context, parser, token):
    """
    Image tags and filters rendered within this tag check for this batch state
    and add to an EasyImageBatch dictionary on the context rather than
    rendering themselves.

    The batch is then generated at once, and the meta dictionary for each
    EasyImage is placed in a dictionary in the render_context that image tags /
    filters in the remainder of the template can access.

    For example::

        {% image_alias 'thumb' as thumb_opts %}

        {% imagebatch %}
        {% for obj in queryset %}
        {{ obj.photo|image:thumb_opts }}
        {% endfor %}
        {% endimagebatch %}

        {% for obj in queryset %}
        <div class="gallery-item">
            <img src="{{ obj.photo|image:thumb_opts }}" alt="{{ obj }}">
        </div>
        {% endfor %}

    Nothing within the ``imagebatch`` tag will be output.
    """
    nodelist = parser.parse(('endimagebatch',))
    parser.delete_first_token()
    return ImagebatchNode(nodelist)
