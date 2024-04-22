from django.db import models


class Profile(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to="profile-images/")
    second_image = models.FileField(upload_to="profile-images/", null=True, blank=True)

    def __str__(self):
        return self.name
