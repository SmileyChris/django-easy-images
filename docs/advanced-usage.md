# Advanced Usage

## Queue Management

### Building Images

Images are built either:

1. Via cron job running `build_img_queue`
2. Or via task runner using the `queued_img` signal

### Manual Queueing

Queue images manually using the `queue` method:

```python
from easy_images import Img
from my_app.models import Product

thumbnail = Img(width=300)
thumbnail.queue(Product, fields=['main_image'])
```

### Automatic Queueing

Automatically queue images when a FileField is saved using [signals](#signals): 

```python
from django.apps import AppConfig
from my_app.images import thumbnail

class MyAppConfig(AppConfig):
    def ready(self):
        from my_app.models import Profile
        thumbnail.queue(Profile, build="src")
```

## Batch Processing

When rendering multiple images (e.g., in a list view), use `ImageBatch` to optimize database queries:

```python
from easy_images import ImageBatch, Img

def product_list_view(request):
    products = Product.objects.all()
    
    # Create a batch for efficient processing
    batch = ImageBatch()
    thumbnail = Img(batch=batch, width=300, format="webp")
    
    # Process all images
    product_images = []
    for product in products:
        bound_img = thumbnail(product.image, alt=product.name)
        product_images.append({
            'product': product,
            'image': bound_img
        })
    
    # First access triggers batch loading of all images
    # Subsequent accesses use cached data
    return render(request, 'products.html', {
        'product_images': product_images
    })
```

### Benefits of Batching

1. **Reduced Database Queries**: One query loads all image metadata instead of N queries
2. **Shared Processing**: Images with the same source share processing results
3. **Memory Efficiency**: Fresh batches prevent memory accumulation
4. **Incremental Loading**: Can add images to already-loaded batches

### Batch Building Strategies

```python
# Option 1: Automatic building on property access (default)
batch = ImageBatch()
img = Img(batch=batch, width=300)
bound = img(file, build="src")
url = bound.base_url()  # Triggers auto-build

# Option 2: Explicit batch building
batch = ImageBatch()
img = Img(batch=batch, width=300)
bound1 = img(file1, build="src")
bound2 = img(file2, build="srcset")
batch.build()  # Build all at once

# Option 3: Immediate building (for signals/queue)
img = Img(width=300)
bound = img(file, build="src", immediate=True)
```

## Performance Tips

1. For high-traffic sites, use `build="src"` to generate base images immediately
2. Use `ImageBatch` when rendering lists of images
3. Set up Celery for distributed image processing
4. Use `format="webp"` for best compression/performance balance
5. Limit `densities` to `[2]` unless high-DPI support is critical (or turn it off entirely)
6. Consider pre-generating common image sizes during deployment

## Signals

### `file_post_save`
Triggered when a FileField is saved. Use to automatically queue images:

```python
from django.apps import AppConfig
from my_app.images import thumbnail

class MyAppConfig(AppConfig):
    def ready(self):
        from my_app.models import Profile
        thumbnail.queue(Profile, build="src")
```

### `queued_img` 
Triggered when images need building. Use with Celery:

```python
from easy_images.management.process_queue import process_queue
from easy_images.signals import queued_img

@app.task
def build_img_queue():
    process_queue()

# In apps.py:
queued_img.connect(lambda **kwargs: build_img_queue.delay(), weak=False)
```

