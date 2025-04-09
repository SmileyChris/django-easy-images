from unittest.mock import MagicMock, patch

import pytest
from django.template import Context, Template, TemplateSyntaxError
from django.utils.safestring import mark_safe


# Mock the Img class and its methods to avoid actual image processing
@patch("easy_images.templatetags.easy_images.Img")
def test_basic_img_tag(MockImg):
    # Setup mock return value for as_html()
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    mock_render_instance.as_html.return_value = '<img src="mock.jpg" alt="Test Alt">'

    template_string = """
    {% load easy_images %}
    {% img mock_file alt="Test Alt" width=100 %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image.jpg"})
    rendered = template.render(context)

    # Assert that Img was called correctly
    MockImg.assert_called_once_with(width=100, quality=80, contain=False, img_attrs={})
    mock_img_instance.assert_called_once_with("path/to/image.jpg", alt="Test Alt")
    mock_render_instance.as_html.assert_called_once()

    # Assert the rendered output
    assert rendered.strip() == '<img src="mock.jpg" alt="Test Alt">'


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_as_variable(MockImg):
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    # Mark the mocked HTML as safe to prevent auto-escaping
    mock_render_instance.as_html.return_value = mark_safe(
        '<img src="mock_as_var.jpg" alt="As Var Test">'
    )

    template_string = """
    {% load easy_images %}
    {% img mock_file alt="As Var Test" width=50 as my_image %}
    <p>Image: {{ my_image }}</p>
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_var.jpg"})
    rendered = template.render(context)

    MockImg.assert_called_once_with(width=50, quality=80, contain=False, img_attrs={})
    mock_img_instance.assert_called_once_with(
        "path/to/image_var.jpg", alt="As Var Test"
    )
    mock_render_instance.as_html.assert_called_once()

    assert (
        '<p>Image: <img src="mock_as_var.jpg" alt="As Var Test"></p>'
        in rendered.strip()
    )
    assert "my_image" in context


def test_img_tag_missing_alt():
    template_string = """
    {% load easy_images %}
    {% img mock_file width=100 %}
    """
    with pytest.raises(TemplateSyntaxError, match="tag requires an alt attribute"):
        Template(template_string)


def test_img_tag_missing_file():
    template_string = """
    {% load easy_images %}
    {% img %}
    """
    with pytest.raises(TemplateSyntaxError, match="tag requires a field file"):
        Template(template_string)


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_with_img_attrs(MockImg):
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    mock_render_instance.as_html.return_value = (
        '<img src="mock_attrs.jpg" alt="Attrs Test" class="test-class" data-id="123">'
    )

    template_string = """
    {% load easy_images %}
    {# Use underscore as token_kwargs seems to handle that better #}
    {% img mock_file alt="Attrs Test" img_class="test-class" img_data_id=123 %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_attrs.jpg"})
    rendered = template.render(context)

    # Check the actual call arguments directly
    MockImg.assert_called_once()  # Check it was called once
    args, kwargs = MockImg.call_args
    assert args == ()
    assert kwargs.get("quality") == 80
    assert kwargs.get("contain") is False
    expected_img_attrs = {"class": "test-class", "data-id": "123"}
    actual_img_attrs = kwargs.get("img_attrs")
    assert actual_img_attrs == expected_img_attrs, (
        f"Expected img_attrs {expected_img_attrs}, got {actual_img_attrs}"
    )
    mock_img_instance.assert_called_once_with(
        "path/to/image_attrs.jpg", alt="Attrs Test"
    )
    mock_render_instance.as_html.assert_called_once()

    assert (
        rendered.strip()
        == '<img src="mock_attrs.jpg" alt="Attrs Test" class="test-class" data-id="123">'
    )


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_with_densities(MockImg):
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    mock_render_instance.as_html.return_value = (
        '<img src="mock_densities.jpg" alt="Densities Test" srcset="...">'  # Simplified
    )

    template_string_str = """
    {% load easy_images %}
    {% img mock_file alt="Densities Test" densities="1.5,2" %}
    """
    template_str = Template(template_string_str)
    context = Context({"mock_file": "path/to/image_densities.jpg"})
    rendered_str = template_str.render(context)

    MockImg.assert_called_once_with(
        densities=[1.5, 2.0], quality=80, contain=False, img_attrs={}
    )
    mock_img_instance.assert_called_once_with(
        "path/to/image_densities.jpg", alt="Densities Test"
    )
    mock_render_instance.as_html.assert_called_once()
    assert 'srcset="..."' in rendered_str  # Basic check

    # Reset mocks for next call
    MockImg.reset_mock()
    mock_img_instance.reset_mock()
    mock_render_instance.reset_mock()
    mock_render_instance.as_html.return_value = (
        '<img src="mock_densities.jpg" alt="Densities Test" srcset="...">'  # Simplified
    )

    template_string_list = """
    {% load easy_images %}
    {% img mock_file alt="Densities Test" densities=density_list %}
    """
    template_list = Template(template_string_list)
    context_list = Context(
        {"mock_file": "path/to/image_densities.jpg", "density_list": [1.0, 3.0]}
    )
    rendered_list = template_list.render(context_list)

    MockImg.assert_called_once_with(
        densities=[1.0, 3.0], quality=80, contain=False, img_attrs={}
    )
    mock_img_instance.assert_called_once_with(
        "path/to/image_densities.jpg", alt="Densities Test"
    )
    mock_render_instance.as_html.assert_called_once()
    assert 'srcset="..."' in rendered_list  # Basic check


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_with_sizes(MockImg):
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    mock_render_instance.as_html.return_value = '<img src="mock_sizes.jpg" alt="Sizes Test" sizes="..." srcset="...">'  # Simplified

    template_string = """
    {% load easy_images %}
    {% img mock_file alt="Sizes Test" size="600,300" size="large,500" %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_sizes.jpg"})
    rendered = template.render(context)

    # Django template kwargs only keep the LAST value for repeated keys
    expected_sizes_last_only = {"large": 500}
    MockImg.assert_called_once_with(
        sizes=expected_sizes_last_only, quality=80, contain=False, img_attrs={}
    )
    mock_img_instance.assert_called_once_with(
        "path/to/image_sizes.jpg", alt="Sizes Test"
    )
    mock_render_instance.as_html.assert_called_once()
    assert 'sizes="..."' in rendered  # Basic check


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_with_format(MockImg):
    mock_img_instance = MockImg.return_value
    mock_render_instance = mock_img_instance.return_value
    mock_render_instance.as_html.return_value = (
        '<img src="mock_format.webp" alt="Format Test">'  # Simplified
    )

    template_string = """
    {% load easy_images %}
    {% img mock_file alt="Format Test" format="webp" %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_format.jpg"})
    rendered = template.render(context)

    MockImg.assert_called_once_with(
        format="webp", quality=80, contain=False, img_attrs={}
    )
    mock_img_instance.assert_called_once_with(
        "path/to/image_format.jpg", alt="Format Test"
    )
    mock_render_instance.as_html.assert_called_once()
    assert 'src="mock_format.webp"' in rendered  # Basic check


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_invalid_option(MockImg):
    template_string = """
    {% load easy_images %}
    {% img mock_file alt="Invalid Test" invalid_option="foo" %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_invalid.jpg"})
    # Update the expected error message based on the new logic
    # ParsedOptions now raises the error during init
    # Expect error from the tag validation, not ParsedOptions
    with pytest.raises(
        ValueError, match="Unknown options passed to 'img' tag: invalid_option"
    ):
        template.render(context)


@patch("easy_images.templatetags.easy_images.Img")
def test_img_tag_invalid_size_format(MockImg):
    template_string = """
    {% load easy_images %}
    {% img mock_file alt="Invalid Size" size="invalid" %}
    """
    template = Template(template_string)
    context = Context({"mock_file": "path/to/image_invalid_size.jpg"})
    with pytest.raises(ValueError, match="size must be a string with a comma"):
        template.render(context)


# Test case for passing an Img instance (less common usage)
@patch("easy_images.templatetags.easy_images.Img", new_callable=MagicMock)
def test_img_tag_with_img_instance(MockImgClass):
    # Mock the instance passed in the context
    mock_context_img_instance = MagicMock()
    mock_render_instance = mock_context_img_instance.return_value
    mock_render_instance.as_html.return_value = (
        '<img src="mock_instance.jpg" alt="Instance Test">'
    )

    template_string = """
    {% load easy_images %}
    {% img mock_file my_img_instance alt="Instance Test" %}
    """
    template = Template(template_string)
    # Pass the mocked Img instance creator in the context
    context = Context(
        {
            "mock_file": "path/to/image_instance.jpg",
            "my_img_instance": mock_context_img_instance,
        }
    )
    rendered = template.render(context)

    # Assert that the Img class itself wasn't called to create a new instance
    MockImgClass.assert_not_called()
    # Assert that the instance from the context was used
    # When using a pre-configured instance, img_attrs from the tag are NOT passed
    # to the instance's __call__ method (as per Img.__call__ signature).
    mock_context_img_instance.assert_called_once_with(
        "path/to/image_instance.jpg", alt="Instance Test"
    )
    mock_render_instance.as_html.assert_called_once()

    assert rendered.strip() == '<img src="mock_instance.jpg" alt="Instance Test">'
