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

## Performance Tips

1. For high-traffic sites, use `build="src"` to generate base images immediately
2. Set up Celery for distributed image processing
3. Use `format="webp"` for best compression/performance balance
4. Limit `densities` to `[2]` unless high-DPI support is critical (or turn it off entirely)
5. Consider pre-generating common image sizes during deployment

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

