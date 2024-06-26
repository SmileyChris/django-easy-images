# Generated by Django 4.2.11 on 2024-04-23 02:13

from django.db import migrations, models

import easy_images.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EasyImage",
            fields=[
                (
                    "id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=easy_images.models.ImageStatus.choices,
                        default=0,
                    ),
                ),
                ("error_count", models.PositiveSmallIntegerField(default=0)),
                ("status_changed_date", models.DateTimeField(null=True)),
                ("storage", models.CharField(max_length=512)),
                ("name", models.CharField(max_length=512)),
                ("args", models.JSONField()),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        height_field="height",
                        storage=easy_images.models.pick_image_storage,
                        upload_to="img/thumbs",
                        width_field="width",
                    ),
                ),
                ("height", models.IntegerField(null=True)),
                ("width", models.IntegerField(null=True)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["storage", "name"], name="easy_images_storage_and_name"
                    )
                ],
            },
        ),
    ]
