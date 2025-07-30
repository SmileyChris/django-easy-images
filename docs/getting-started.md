# Getting Started

## Installation

```bash
pip install django-easy-images
```

Add to your Django settings:
```python
INSTALLED_APPS = [
    "easy_images",
    # ...
]
```

### Dependencies
You'll need [libvips](https://www.libvips.org/install.html) installed:

- **MacOS**: `brew install vips`
- **Ubuntu**: `sudo apt-get install --no-install-recommends libvips`
- **Arch**: `sudo pacman -S libvips`

## Basic Usage

### Using the Img class
```python
from easy_images import Img

# Create an image configuration
thumb = Img(width="md")

# Generate HTML for an image
html = thumb(profile.photo, alt="Profile photo").as_html()
```

### Batch Processing for Multiple Images

When working with multiple images, use `ImageBatch` for better performance:

```python
from easy_images import Img, ImageBatch

# Create a batch for efficient processing
batch = ImageBatch()
thumb = Img(batch=batch, width="md")

# Process multiple images
images = []
for profile in profiles:
    bound_img = thumb(profile.photo, alt=f"{profile.name}'s photo")
    images.append(bound_img)

# First access loads all images in one query
for img in images:
    print(img.as_html())
```

See the [API documentation](api.md#imagebatch-batch-processing) for more details.

### Using template tags
```html
{% load easy_images %}

<!-- Basic usage -->
{% img report.image width="md" alt="" %}

<!-- With predefined Img instance -->
{% img report.image thumb alt="" %}
```

## Next Steps
- [Configuration Options](configuration.md)
- [Advanced Usage](advanced-usage.md)