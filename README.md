
# Django easy images

Easily build responsive HTML `<img>` tags by thumbnailing Django images using the VIPS fast image processing library.

When an `<img>` is generated, any thumbnails that don't already exist are queued for building (if aren't already queued) and left out of the HTML.
For example, an image built from `Img(width="md")` will generate:

```html
<img src="/media/img/profiles/john.jpg" alt="Profile photo for John Doe">
```

But after the images are built, the HTML will be:

```html
<img
  src="/media/img/thumbs/f52fbd32b2b3b86ff88ef6c490628285.jpg"
  srcset="
    /media/img/thumbs/18183dd9009f2b7e1b44f9c4af287589.webp,
    /media/img/thumbs/fb8c2e2b85ca81eb4350199faddd983c.webp 2x
  "
  alt="Profile photo for John Doe"
>
```

## Installation & Configuration

To install django-easy-images, simply run the following command:

```bash
pip install django-easy-images
```

Once installed, add the `easy_images` app in your Django settings file:

```python
INSTALLED_APPS = [
    "easy_images",
    # ...
]
```
Since this uses pyvips, you'll need to have the [libvips library installed on your system](https://www.libvips.org/install.html).

## Documentation

Project documentation is built using [mkdocs](https://www.mkdocs.org/). To build and serve the documentation locally:

```bash
pip install mkdocs
mkdocs serve
```

Then open http://localhost:8000 in your browser.

The documentation includes:
- Usage examples
- API reference
- Configuration options
Since this uses pyvips, you'll need to have the [libvips library installed on your system](https://www.libvips.org/install.html).

<table>

<tr>
<td>MacOs</td>
<td>
<code>
brew install vips
</code>
</td>
</tr>

<tr>
<td>Ubuntu</td>
<td>
<code>
sudo apt-get install --no-install-recommends libvips
</code>
</td>
</tr>

<tr>
<td>Arch</td>
<td>
<code>
sudo pacman -S libvips
</code>
</td>
</tr>

</table>

## Usage

You use the `Img` class or `{% img %}` template tag to render a Django FieldFile (or ImageFieldFile) containing an image as a responsive HTML `<img>` tag.

### Summary

1. Define your `Img` classes in your app's `images.py` file.
2. Use these in your views / templates to generate the `<img>` tags.
3. Either set up a cron job to run the `build_img_queue` management command to build images, or use a celery task and the `queued_img` signal to build images as they are queued.
4. Optionally, use the `Img.queue` method in your `apps.py` file to queue images for building as soon as they are uploaded (building the src/srcset inline if needed).

### Img class

The `Img` class is used to create a generator for HTML `<img>` elements. Here's an example of how to use it:

```python
from easy_images import Img
thumb = Img(width="md")
thumb(profile.photo, alt=f"Profile photo for {{ profile.name }}").as_html()
```

As you can see, `thumb` is an `Img` instance that is used to generate an HTML `<img>` element for the `profile.photo` image. The output would look something like this:

```html
<img
  src="/media/img/thumbs/f52fbd32b2b3b86ff88ef6c490628285.jpg"
  srcset="
    /media/img/thumbs/18183dd9009f2b7e1b44f9c4af287589.webp,
    /media/img/thumbs/fb8c2e2b85ca81eb4350199faddd983c.webp 2x
  "
  alt="Profile photo for John Doe"
/>
```

In the following [options section](#options) you can see all the different options that you can pass to the `Img` instance.

There other optional arguments that you can pass to the instance:

#### `alt`

The `alt` text for the image.

#### `build`

Determines determines what should be built inline. Valid values are:

- `None`: All images will be built out-of-band from the request *(default)*.
- `"src"`: The base `src` image will be built inline, but the `srcset` images will be built out-of-band from the request.
- `"srcset"`: Both the base `src` image and all `srcset` images will be built inline.

#### `img_attrs`

A dictionary of any additional attributes to add to the `<img>` element.

### The `{% img %}` tag

The `img` template tag is another way to generate a responsive HTML `<img>` element.

```jinja
{% load easy_images %}
{% img report.image width="md" alt="" %}
```

You can also pass a `Img` instance to the `img` template tag:

```jinja
{% load easy_images %}
{% img report.image thumb alt="" %}
```

The template tag never builds images inline.

## Building images.

Whenever a image is requested, any image versions not already built will be queued for building and excluded from the HTML.

To build the images in this queue, you can either:

- run the `build_img_queue` management command (usually in a cron job), or
- process it in a task using celery or another task runner (probably using the [`queued_img` signal](#queued_img-signal)).

## Options

The `Img` class and the `img` template tag can be called with the following options.

#### `width`

Limit the width of the image. Either use an integer, or one of the following tailwind sizes as a string: "xs", "sm", "md", "lg", "screen-sm", "screen-md", "screen-lg", "screen-xl" or "screen-2xl"

#### `ratio`

The aspect ratio of the image to build.

Use a float representing the ratio (e.g. `4/5`) or one of the following strings: "square", "video" (meaning 16/9), "video_vertical", "golden" (using the golden ratio), "golden_vertical".

The default is `"video"` (16/9).

#### `crop`

Whether to crop the image.

The default is `True`.

Use a boolean, or tuple of two floats, or the comma separated string equivalent. `True` is replaced with to `(0.5, 0.5)` meaning the image is cropped from the center. The numbers are percentages of the image size.

You can also use the following keywords: `tl` (top left), `tr` (top right), `bl` (bottom left), `br` (bottom right), `l`, `r`, `t` or `b`. This will set the percentage to 0 or 100 for the appropriate axis.

If crop is `False`, the image will be resized so that it will cover the requested ratio but not cropped down.
This is useful when you want to handle positioning in CSS using `object-fit`.

#### `contain`

When resizing the image (and not cropping), contain the image within the requested ratio. This ensures it will always fit within the requested dimensions. It also stops the image from being upscaled.

The default is `False`, meaning the image will be resized down to cover the requested ratio (which means the image dimensions may be larger than the requested dimensions).

#### `focal_window`

A focal window to zoom in on when shrinking the image. Use a tuple of four floats (or a comma separated string equivalent) where the first pair of percentages is the top left corner and the second pair of percentages is the bottom right corner.

#### `quality`

The quality of the image. For example, `quality=90` means that the image will be compressed with a quality of 90. The default is 80.

#### `densities`

A list of higher density versions of the image to also create.

The default is `[2]`.

#### `sizes`

A dictionary of sizes to use at different media queries. The keys should either be an integer to represent a max-width, or a string to represent a specific media query. The keys can either be an int/string to represent the width, or a dictionary of options (that must contain a width).

If `densities` is set, a higher density version of the largest size (excluding 'print' media) will also be built to give the browser more options.

For example:

```python
img_with_sizes = Img(
    # Base size
    width=300,
    # Alternate sizes for different media queries
    sizes={
        # Print media query, larger width with higher quality
        "print": {"width": 450, "quality": 90},
        # A viewport max width of 800, smaller width.
        800: 100
    },
)
print(img_with_sizes(model_instance.image, build="srcset").as_html())
```

will output:

```html
<img src="/media/img/thumbs/08efa8f7b11b7e9b24a037bb3f216369.jpg" srcset="/media/img/thumbs/18183dd9009f2b7e1b44f9c4af287589.webp 100w, /media/img/thumbs/08efa8f7b11b7e9b24a037bb3f216369.webp 300w, /media/img/thumbs/fb8c2e2b85ca81eb4350199faddd983c.webp 450w, /media/img/thumbs/cfca1aebe161e09926c86f76d4e2f1b4.webp 600w" sizes="(print) 450px, (max-width: 800) 100px" alt="">
```

#### `format`

The image format to build the `srcset` versions with. The valid values are `"webp"` *(default)*, `"avif"` or `"jpeg"`. 
Note that AVIF uses a lot of memory to build images. 

The base `src` image format will always be built as a JPEG for backwards compatibility.

## Signals

### Queue from model.

### `file_post_save` signal

This signal is triggered for each that `FileField` that was uncommitted when it's model instance is saved.

It can be used to build & pre-queue images for a model instance.

The most simplest usage is via the `Img` instance's helper method called `queue`. Here's an example of using that in a model's `apps.py` file:

```python
from django.apps import AppConfig

from my_app.images import thumbnail

class MyAppConfig(AppConfig):
    name = 'my_app'

    def ready(self):
        from my_app.models import Profile

        thumbnail.queue(Profile, build="src")
```

By default, `queue` listens for saves to any `ImageField` on the model. Use the `fields` argument to limit which fields to queue images for:
* `None` means all file fields on the model
* a field class or subclass that the field must be *(default is `ImageField`)*
* a list of field names to match (the signal will still only fire on file fields)

### `queued_img` signal

This signal is triggered whenever an image element is missing and was not already queued for building.

It can be used to process the queue in a task using celery or another task runner. Here's an example `tasks.py`:

```python
from easy_images.management.process_queue import process_queue

@app.task
def build_img_queue():
    process_queue()
```

In your apps `apps.py` file, connect this receiver:

```python
from django.apps import AppConfig

from easy_images.signals import queued_img

class MyAppConfig(AppConfig):
    name = 'my_app'

    def ready(self):
        from my_app.tasks import build_img_queue

        # Kick off build task as soon as any image is queued.
        queued_img.connect(lambda **kwargs: build_img_queue.delay(), weak=False)
        # Also start the build task as soon as the app is ready in case there are already queued images.
        build_img_queue.delay()
```
