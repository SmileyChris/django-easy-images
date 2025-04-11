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
```python
from easy_images import ImageBatch

batch = ImageBatch()
img1 = batch.add(source_file=model1.image_field, options={'width': 800})
img2 = batch.add(source_file=model2.image_field, options={'width': 600})

# Get HTML for all images
html1 = img1.as_html()
html2 = img2.as_html()
```

#### `BoundImg` - Processed Image
```python
# Get image URLs
main_url = processed_img.base_url()
srcset = processed_img.srcset  # List of available sizes

# Build images immediately (instead of queue)
processed_img.build('all')  # Options: 'all', 'base', 'srcset'
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