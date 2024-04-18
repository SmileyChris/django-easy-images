import pytest
from django.db.models import F, FileField, Value
from django.db.models.fields.files import FieldFile
from django.db.models.functions import Concat

from easy_images.core import Img
from easy_images.models import EasyImage


@pytest.mark.django_db
def test_as_html():
    generator = Img(width=100)
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    assert generator(source).as_html() == '<img src="/test.jpg" alt="">'
    EasyImage.objects.update(
        image=Concat(F("args__mimetype"), F("args__width"), Value(".image")),
        width=800,
        height=600,
    )
    assert generator(source).as_html() == (
        '<img src="/image/jpeg100.image" srcset="/image/avif100.image, /image/avif200.image 2x" alt="">'
    )


@pytest.mark.django_db
def test_sizes():
    generator = Img(width=200, sizes={800: 100})
    source = FieldFile(instance=EasyImage(), field=FileField(), name="test.jpg")
    assert generator(source).as_html() == '<img src="/test.jpg" alt="">'
    EasyImage.objects.update(
        image=Concat(F("args__mimetype"), F("args__width"), Value(".image")),
        width=800,
        height=600,
    )
    assert generator(source).as_html() == (
        '<img src="/image/jpeg200.image"'
        ' srcset="/image/avif100.image 100w, /image/avif200.image 200w, /image/avif400.image 400w"'
        ' sizes="(max-width: 800px) 100px, 200px" alt="">'
    )
