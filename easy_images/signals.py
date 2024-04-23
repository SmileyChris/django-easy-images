import django.dispatch
from django.db.models import FileField

file_post_save = django.dispatch.Signal()
"""
A signal sent after a model save for each ``FileField`` that was uncommitted before the
save.

* The ``sender`` argument will be the model class.
* The ``fieldfile`` argument will be the instance of the field's file that was saved.
"""

queued_img = django.dispatch.Signal()
"""
A signal sent when an ``Img`` queues images for building.

* The ``sender`` argument will be the ``Img`` instance.
* The ``instance`` argument will be the instance of the field's file.
"""


def find_uncommitted_filefields(sender, instance, **kwargs):
    """
    A pre_save signal handler which attaches an attribute to the model instance
    containing all uncommitted ``FileField``s, which can then be used by the
    :func:`signal_committed_filefields` post_save handler.
    """
    from easy_images.models import EasyImage

    if issubclass(sender, EasyImage):
        # Don't record uncommitted fields for EasyImage instances.
        return
    uncommitted = instance._uncommitted_filefields = []

    fields = [f for f in sender._meta.get_fields() if isinstance(f, FileField)]
    if kwargs.get("update_fields", None):
        # Limit to the fields that are being updated.
        fields = [f for f in fields if f.name in kwargs["update_fields"]]
    for field in fields:
        fieldfile = getattr(instance, field.name)
        if fieldfile and not fieldfile._committed:
            uncommitted.append(field.name)


def signal_committed_filefields(sender, instance, **kwargs):
    """
    A post_save signal handler which sends a signal for each ``FileField`` that
    was committed this save.
    """
    for field_name in getattr(instance, "_uncommitted_filefields", ()):
        fieldfile = getattr(instance, field_name)
        # Don't send the signal for deleted files.
        if fieldfile:
            file_post_save.send(sender=sender, fieldfile=fieldfile)
