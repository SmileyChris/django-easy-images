# API Reference

## Core Modules

### `easy_images.core`

Main functionality for image processing with these key classes:

#### `Img` - Image Configuration
```python
from easy_images import Img

# Basic usage
img = Img(width=800, format='webp', quality=85)
processed_img = img(my_model.image_field)

# Chaining configurations
responsive_img = (
    Img(width=1200)
    .extend(width=800, sizes={'768': 600, '480': 400})
)

# Automatic processing on model save
img.queue(MyModel)  # Processes all ImageFields on MyModel
```

#### `ImageBatch` - Batch Processing

The `ImageBatch` class optimizes database queries when processing multiple images:

```python
from easy_images import ImageBatch, Img

# Create a shared batch for efficient processing
batch = ImageBatch()

# Create image configurations with the batch
img = Img(batch=batch, width=800, format="webp")
thumbnail = Img(batch=batch, width=200, format="jpg")

# Add images to the batch
bound1 = img(model1.image_field, alt="Main image")
bound2 = thumbnail(model2.image_field, alt="Thumbnail")

# Access images - batch loading happens automatically
html1 = bound1.as_html()  # First access triggers batch loading
html2 = bound2.as_html()  # Already loaded, no extra queries

# Or explicitly build all images in the batch
batch.build()
```

**Key benefits:**
- Batches database queries for multiple images
- Shares loaded image data across all items in the batch
- Supports incremental loading when adding images to an already-loaded batch
- Automatic lazy building when properties are accessed

#### `BoundImg` - Processed Image

A `BoundImg` represents a single image item within a batch:

```python
# Properties (trigger auto-building if needed)
main_url = bound_img.base_url()           # URL of the base image
srcset_items = bound_img.srcset          # List of SrcSetItem objects
alt_text = bound_img.alt                  # Alt text
sizes_attr = bound_img.sizes             # Sizes attribute for responsive images
html = bound_img.as_html()               # Complete <img> tag

# Check if images are built
if bound_img.is_built:
    print("Images are ready")

# Manually trigger building
bound_img.build('all')  # Options: 'all', 'src', 'srcset'
```

### `easy_images.engine`
Image processing engine implementation

### `easy_images.models`
Database models for storing image information

## Management Commands

### `build_img_queue`
Processes pending images in the queue:
```bash
python manage.py build_img_queue
```

## Template Tags

### `easy_images`
Template tags for rendering processed images:
```html
{% load easy_images %}

<!-- Basic usage -->
{% easy_image obj.image_field width=800 %}

<!-- With responsive sizes -->
{% easy_image obj.image_field width=1200 sizes="(max-width: 768px) 600px, (max-width: 480px) 400px" %}
```