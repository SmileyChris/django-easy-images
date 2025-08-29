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

### `easy_images`

Manages the EasyImage queue with subcommands for building, requeuing, and checking status. This is the primary command for managing image processing.

#### Basic Usage

```bash
# Show queue status (default action)
python manage.py easy_images
python manage.py easy_images status

# Build queued images
python manage.py easy_images build

# Requeue failed images
python manage.py easy_images requeue
```

#### Subcommands

##### `status` (default)
Shows queue statistics and current state. Supports multiple output formats and health gates:

```bash
# Auto format: pretty on TTY, plain otherwise
python manage.py easy_images status

# Explicit formats
python manage.py easy_images status --format pretty
python manage.py easy_images status --format plain
python manage.py easy_images status --format json

# Options
python manage.py easy_images status --stale-after 600   # Stale BUILDING threshold (seconds)
python manage.py easy_images status --verbose           # Show error distribution
python manage.py easy_images status --fail-on-stale     # Exit non-zero if stale builds exist
python manage.py easy_images status --fail-on-errors 5  # Exit non-zero if errors > 5
```

Plain/pretty output includes:
- Total source images (distinct storage+name)
- Total generated images
- Total images in queue (unbuilt: queued+building+errors)
- Average generated per source
- Breakdown by status (queued, building with stale count, errors split by type)
- Error count distribution (with `--verbose`)
- Suggestions (commands to remediate)

Example (pretty):

```
Summary: 7 sources | 3 generated (0.43/src) | 5 queued | 2 building (1 stale) | 2 errors (S:1 B:1)

Totals:
  Total source images: 7
  Total generated images: 3
  Total images in queue: 5
  Avg generated per source: 0.43

Breakdown:
  Queued:   5 █████
  Building: 2 ██ (1 stale > 600s)
  Errors:   2 ██ (source: 1, build: 1)

Suggestions:
  python manage.py easy_images build --stale-after 600
  python manage.py easy_images requeue --max-errors 3
```

JSON schema:

```json
{
  "counts": {
    "sources": 7,
    "generated": 3,
    "queued": 5,
    "building": 2,
    "source_errors": 1,
    "build_errors": 1
  },
  "avg_per_source": 0.43,
  "stale": { "threshold_seconds": 600, "count": 1 },
  "error_dist": [{ "error_count": 1, "count": 2 }],
  "suggestions": [
    "python manage.py easy_images build --stale-after 600",
    "python manage.py easy_images requeue --max-errors 3"
  ]
}
```

##### `build`
Processes queued images with intelligent stale detection:

```bash
python manage.py easy_images build
python manage.py easy_images build --stale-after 300      # Stale if BUILDING > 5 minutes
python manage.py easy_images build --max-errors 3         # Skip images with > 3 errors
python manage.py easy_images build --verbose              # Show detailed progress
```

Options:
- `--stale-after <seconds>` - Images stuck in BUILDING status longer than this are considered stale and reprocessed (default: 600 seconds)
- `--max-errors <count>` - Only retry images with at most this many previous errors
- `--verbose` - Show detailed progress and error information

##### `requeue`
Resets failed images back to QUEUED status for reprocessing:

```bash
python manage.py easy_images requeue
python manage.py easy_images requeue --max-errors 5       # Only if ≤ 5 errors
python manage.py easy_images requeue --include-stale      # Also requeue stale builds
```

Options:
- `--max-errors <count>` - Only requeue images with at most this many errors
- `--include-stale` - Also requeue images stuck in BUILDING status
- `--stale-after <seconds>` - With --include-stale, defines stale threshold (default: 600)

#### Image Processing States

- **Queued** - New images waiting to be processed
- **Building** - Images currently being processed (auto-detected as stale if too old)
- **Built** - Successfully processed images
- **Source Error** - Source file couldn't be accessed
- **Build Error** - Failed during processing

#### Smart Stale Detection

The command automatically handles crashed or stuck builds by checking the `status_changed_date`:
- Images in BUILDING status with recent timestamps are skipped (actually building)
- Images in BUILDING status with old timestamps are treated as stale and reprocessed
- No need for manual `--force` flag in most cases

#### Integration Examples

1. **Cron Job** - Regular processing with automatic stale handling:
   ```bash
   # Process queue every 5 minutes
   */5 * * * * /path/to/python /path/to/manage.py easy_images build
   ```

2. **Error Recovery Workflow**:
   ```bash
   # Check current status
   python manage.py easy_images
   
   # Requeue failed images with < 3 errors
   python manage.py easy_images requeue --max-errors 3
   
   # Process the requeued images
   python manage.py easy_images build
   ```

3. **Monitoring Script**:
   ```bash
   # Pretty output for humans (TTY)
   python manage.py easy_images status --stale-after 600 --verbose

   # JSON for machines
   python manage.py easy_images status --format json --stale-after 600

   # Fail CI/monitoring if stale builds or too many errors
   python manage.py easy_images status --fail-on-stale --fail-on-errors 0
   ```

### `build_img_queue` (Deprecated)

**⚠️ Deprecated:** This command is maintained for backwards compatibility. Please use `easy_images build` instead.

```bash
# Old command (deprecated)
python manage.py build_img_queue --retry 3

# New equivalent
python manage.py easy_images build --max-errors 3
```

The old command will continue to work but displays a deprecation warning. It maps to the new command with these defaults:
- `--retry` → `--max-errors`
- Stale detection enabled with 600 second threshold
- All other behavior remains the same

## Template Tags

### `easy_images`
Template tags for rendering processed images:
```html
{% load easy_images %}

<!-- Basic usage -->
{% easy_image obj.image_field width=800 %}

<!-- With responsive sizes -->
{% easy_image obj.image_field width=1200 sizes="(max-width: 768px) 600px, (max-width: 480px) 400px" %}

<!-- With additional HTML attributes using img_ prefix -->
{% img obj.image_field width="md" alt="Product" img_class="rounded-lg" img_loading="lazy" img_data_id="123" %}
```

The template tag supports adding custom HTML attributes to the generated `<img>` element by prefixing them with `img_`. For example:
- `img_class="my-class"` becomes `class="my-class"`
- `img_loading="lazy"` becomes `loading="lazy"`
- `img_data_id="123"` becomes `data-id="123"`
