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

If you're going to be building several images, consider using the [`ImageBatch`](api.md#imagebatch) class to process them in bulk.

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