from unittest import TestCase
from easy_images.image import EasyImage
from easy_images.tests import models


class FieldTargetTest(TestCase):

    def test_no_target_fields(self):
        anmial = models.Animal(name='Cat', photo='keyboardcat.jpg')
        image = EasyImage(anmial.photo, {'crop': (32, 32)})
        self.assertEqual(image.opts, {'crop': (32, 32)})

    def test_default_target_fields(self):
        person = models.Person(
            name='Bob', photo='bob.jpg', photo_targetx=10, photo_targety=20)
        image = EasyImage(person.photo, {'crop': (32, 32)})
        self.assertEqual(image.opts, {'crop': (32, 32), 'target': (10, 20)})

    def test_custom_target_fields(self):
        food = models.Food(
            name='Broccoli', photo='broccoli.jpg', targetx=10, targety=20)
        image = EasyImage(food.photo, {'crop': (32, 32)})
        self.assertEqual(image.opts, {'crop': (32, 32), 'target': (10, 20)})

    def test_target_fields_blank(self):
        food = models.Food(
            name='Broccoli', photo='broccoli.jpg')
        image = EasyImage(food.photo, {'crop': (32, 32)})
        self.assertEqual(image.opts, {'crop': (32, 32)})

    def test_target_fields_partial(self):
        apple = models.Food(name='Apple', photo='apple.jpg', targetx=100)
        banana = models.Food(name='Banana', photo='banana.jpg', targety=0)
        self.assertEqual(
            EasyImage(apple.photo, {'crop': (32, 32)}).opts,
            {'crop': (32, 32), 'target': (100, 50)})
        self.assertEqual(
            EasyImage(banana.photo, {'crop': (32, 32)}).opts,
            {'crop': (32, 32), 'target': (50, 0)})

    def test_target_fields_middle(self):
        carrot = models.Food(
            name='Carrot', photo='carrot.jpg', targetx=50, targety=50)
        self.assertEqual(
            EasyImage(carrot.photo, {'crop': (32, 32)}).opts,
            {'crop': (32, 32)})


class FieldAliasTest(TestCase):

    def test_alias(self):
        adam = models.Person('Adam', 'adam.jpg')
        self.assertEqual(
            adam.photo['square'].opts, {'crop': (32, 32), 'upscale': True})

    def test_bad_alias(self):
        adam = models.Person('Adam', 'adam.jpg')
        self.assertRaises(KeyError, lambda: adam.photo['sqaure'])
