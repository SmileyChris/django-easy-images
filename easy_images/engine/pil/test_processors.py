from unittest import TestCase

from PIL import Image, ImageChops, ImageDraw

from . import processors


def create_image(mode='RGB', size=(80, 60)):
    image = Image.new(mode, size, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    x_bit, y_bit = size[0] // 10, size[1] // 10
    draw.rectangle((x_bit, y_bit * 2, x_bit * 7, y_bit * 3), 'red')
    draw.rectangle((x_bit * 2, y_bit, x_bit * 3, y_bit * 8), 'red')
    return image


class ResizeTest(TestCase):

    def assertImagesEqual(self, im1, im2, msg=None):
        if im1.size != im2.size or (
                ImageChops.difference(im1, im2).getbbox() is not None):
            raise self.failureException(
                msg or 'The two images were not identical')  # pragma: no cover

    def test_noop(self):
        image = create_image()
        returned_image = processors.resize(image)
        self.assertIs(image, returned_image)

    def test_fit(self):
        image = create_image()

        fit = processors.resize(image, fit=(40, 40))
        self.assertEqual(fit.size, (40, 30))

        unchanged = processors.resize(image, fit=(100, 100))
        self.assertEqual(unchanged.size, (80, 60))
        self.assertIs(unchanged, image)

        upscaled = processors.resize(image, fit=(100, 100), upscale=True)
        self.assertEqual(upscaled.size, (100, 75))

    def test_crop(self):
        image = create_image()

        both_cropped = processors.resize(image, crop=(40, 40))
        self.assertEqual(both_cropped.size, (40, 40))

        not_cropped = processors.resize(image, crop=(100, 100))
        self.assertEqual(not_cropped.size, (80, 60))

        x_cropped = processors.resize(image, crop=(60, 60))
        expected = image.crop([10, 0, 70, 60])
        self.assertImagesEqual(x_cropped, expected)

        y_cropped = processors.resize(image, crop=(100, 10))
        expected = image.crop([0, 25, 80, 35])
        self.assertImagesEqual(y_cropped, expected)

    def test_crop_smart(self):
        image = create_image(size=(800, 600))
        smart_crop = processors.resize(image, crop=(600, 600), smart_crop=True)
        expected = image.crop([78, 0, 678, 600])
        self.assertImagesEqual(smart_crop, expected)

    def test_fill(self):
        image = create_image(size=(20, 40))

        filled = processors.resize(image, fill=(10, 10))
        self.assertEqual(filled.size, (10, 20))

        filled = processors.resize(image, fill=(60, 60))
        self.assertEqual(filled.size, (20, 40))

        filled = processors.resize(image, fill=(60, 60), upscale=True)
        self.assertEqual(filled.size, (60, 120))

    def test_one_dimension_fit(self):
        image = create_image()

        scaled = processors.resize(image, fit=(40, 0))
        self.assertEqual(scaled.size, (40, 30))
        scaled = processors.resize(image, fit=(0, 40))
        self.assertEqual(scaled.size, (53, 40))

    def test_one_dimension_crop(self):
        image = create_image()

        cropped = processors.resize(image, crop=(40, 0))
        self.assertEqual(cropped.size, (40, 30))
        cropped = processors.resize(image, crop=(0, 40))
        self.assertEqual(cropped.size, (53, 40))

    def test_croup_rounding(self):
        image = create_image(size=(240, 362))

        size = (11, 100)
        cropped = processors.resize(image, crop=size)
        self.assertEqual(cropped.size, size)

    def test_zoom_fit(self):
        image = create_image(size=(240, 362))

        size = (10, 10)
        scaled = processors.resize(image, fit=size, zoom=40)
        self.assertEqual(scaled.size, (7, 10))

    def test_zoom_crop(self):
        image = create_image(size=(240, 362))

        size = (11, 100)
        cropped = processors.resize(image, crop=size, zoom=40)
        self.assertEqual(cropped.size, size)

    def test_crop_target(self):
        image = create_image()

        # Try bottom right target.
        target = (95, 100)

        tl_crop = processors.resize(
            image, crop=(10, 60), target=target)
        expected = image.crop([70, 0, 80, 60])
        self.assertImagesEqual(tl_crop, expected)

        tl_crop = processors.resize(
            image, crop=(80, 10), target=target)
        expected = image.crop([0, 50, 80, 60])
        self.assertImagesEqual(tl_crop, expected)

        # Top left target.
        target = (0, 5)

        tl_crop = processors.resize(
            image, crop=(10, 60), target=target)
        expected = image.crop([0, 0, 10, 60])
        self.assertImagesEqual(tl_crop, expected)

        tl_crop = processors.resize(
            image, crop=(80, 10), target=target)
        expected = image.crop([0, 0, 80, 10])
        self.assertImagesEqual(tl_crop, expected)


class ColorspaceTest(TestCase):

    def test_standard(self):
        image = Image.new('RGB', (80, 60))
        processed = processors.colorspace(image)
        self.assertEqual(processed.mode, 'RGB')

        image = Image.new('L', (80, 60))
        processed = processors.colorspace(image)
        self.assertEqual(processed.mode, 'L')

    def test_transparent(self):
        image = Image.new('RGBA', (80, 60))
        processed = processors.colorspace(image)
        self.assertEqual(processed.mode, 'RGBA')

        image = Image.new('LA', (80, 60))
        processed = processors.colorspace(image)
        self.assertEqual(processed.mode, 'LA')

    def test_replace_alpha(self):
        image = Image.new('RGBA', (80, 60))
        self.assertEqual(image.load()[0, 0], (0, 0, 0, 0))
        processed = processors.colorspace(image, replace_alpha='#fefdfc')
        self.assertEqual(processed.mode, 'RGB')
        self.assertEqual(processed.load()[0, 0], (254, 253, 252))

        image = Image.new('LA', (80, 60))
        self.assertEqual(image.load()[0, 0], (0, 0))
        processed = processors.colorspace(image, replace_alpha='#fefdfc')
        self.assertEqual(processed.mode, 'L')
        self.assertEqual(processed.load()[0, 0], 253)

    def test_bw(self):
        image = Image.new('RGB', (80, 60))
        processed = processors.colorspace(image, bw=True)
        self.assertEqual(processed.mode, 'L')

        image = Image.new('RGBA', (80, 60))
        processed = processors.colorspace(image, bw=True)
        self.assertEqual(processed.mode, 'LA')

        image = Image.new('L', (80, 60))
        processed = processors.colorspace(image, bw=True)
        self.assertEqual(processed.mode, 'L')

        image = Image.new('LA', (80, 60))
        processed = processors.colorspace(image, bw=True)
        self.assertEqual(processed.mode, 'LA')


class AutocropTest(TestCase):

    def test_standard(self):
        processed = processors.autocrop(create_image(), autocrop=True)
        self.assertEqual(processed.size, (49, 43))


class BackgroundTest(TestCase):

    def test_basic(self):
        image = create_image()
        processed = processors.background(
            image, background='#fff', fit=(80, 80))
        self.assertEqual(processed.size, (80, 80))

    def test_grayscale(self):
        image = create_image().convert('L')
        processed = processors.background(
            image, background='#fff', fit=(80, 80))
        self.assertEqual(processed.size, (80, 80))
        self.assertEqual(processed.mode, 'L')

    def test_mode_alpha(self):
        image = create_image().convert('RGBA')
        processed = processors.background(
            image, background='#fff', fit=(80, 80))
        self.assertEqual(processed.size, (80, 80))
        self.assertEqual(processed.mode, 'RGB')

        image = create_image().convert('LA')
        processed = processors.background(
            image, background='#fff', fit=(80, 80))
        self.assertEqual(processed.size, (80, 80))
        self.assertEqual(processed.mode, 'L')
