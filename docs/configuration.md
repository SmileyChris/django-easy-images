# Configuration Options

## Image Processing Options

### `width`
Limit the width of the image. Can be:

- Integer (pixels)
- Tailwind size string: "xs", "sm", "md", "lg", "screen-sm", "screen-md", "screen-lg", "screen-xl", "screen-2xl"

```python
Img(width=300)  # Fixed width
Img(width="md")  # Responsive width
```

### `ratio`
The aspect ratio of the image. Can be:

- Float (e.g. `4/5`)
- String: "square", "video" (16/9), "video_vertical", "golden", "golden_vertical"

```python
Img(ratio="square")  # 1:1 ratio
Img(ratio=16/9)      # Custom ratio
```

### `crop`
How to crop the image:

- `True` (default): Crop from center (0.5, 0.5)
- `False`: Don't crop (use CSS object-fit instead)
- Tuple: (x%, y%) crop position
- String: Position keywords like "tl", "tr", "bl", "br", "l", "r", "t", "b"

```python
Img(crop="tl")  # Crop from top-left
Img(crop=False) # No cropping
```

### `quality`
Image compression quality (default: 80)

```python
Img(quality=90)  # Higher quality
```

## Advanced Options

### `sizes`
Responsive sizes for different media queries:

```python
Img(
    width=300,
    sizes={
        "print": {"width": 450, "quality": 90},
        800: 100  # Max-width 800px
    }
)
```

### `format`
`srcset` image format (default: "webp"):

- "webp" (recommended)
- "avif" (memory intensive)
- "jpeg"

```python
Img(format="avif")  # Use AVIF format
```

### `focal_window`
Zoom area specified as (x1%, y1%, x2%, y2%):

```python
Img(focal_window=(25, 25, 75, 75))  # Zoom center 50% of image
```

### `densities`
Higher density versions to generate (default: `[2]`):

```python
Img(densities=[1.5, 2, 3])  # Generate 1.5x, 2x and 3x versions
```