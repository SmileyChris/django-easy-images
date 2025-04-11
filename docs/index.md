# Django Easy Images Documentation

Welcome to the documentation for Django Easy Images - a powerful image processing solution for Django projects.

## What is Django Easy Images?

Django Easy Images makes it simple to:

- Generate responsive HTML `<img>` tags
- Automatically create thumbnails and optimized versions
- Queue image processing for better performance
- Support modern formats like WebP and AVIF

## Quick Start

```python
from easy_images import Img

# Create a thumbnail configuration
profile_thumb = Img(width=200, ratio="square")

# Generate HTML for a profile photo
html = profile_thumb(user.profile.photo, alt="User profile").as_html()
```

## Documentation Sections

1. [Getting Started](getting-started.md) - Installation and basic usage
2. [Configuration](configuration.md) - All available image processing options
3. [Advanced Usage](advanced-usage.md) - Signals, queue management and performance tips
4. [API Reference](api.md) - Detailed technical documentation

## Need Help?

Found an issue or have questions? Please [open an issue](https://github.com/SmileyChris/django-easy-images) on GitHub.