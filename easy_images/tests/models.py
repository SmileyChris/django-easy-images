from django.db import models
from easy_images.fields import EasyImageField


class Animal(models.Model):
    name = models.CharField(max_length=50)
    photo = EasyImageField()


class Person(models.Model):
    name = models.CharField(max_length=50)
    photo = EasyImageField()
    photo_targetx = models.PositiveSmallIntegerField(null=True)
    photo_targety = models.PositiveSmallIntegerField(null=True)


class Food(models.Model):
    name = models.CharField(max_length=50)
    photo = EasyImageField(targetx_field='targetx', targety_field='targety')
    targetx = models.PositiveSmallIntegerField(null=True)
    targety = models.PositiveSmallIntegerField(null=True)
