"""
image = EasyImageField(..., targetx_field, targety_field, build)


"""
from django.db.models.fields.files import ImageField, ImageFieldFile
from easy_images.aliases import aliases
from easy_images.image import EasyImage


class EasyImageFieldFile(ImageFieldFile):

    @property
    def default_opts(self):
        """
        Add the target from this FieldFile's instance if the field provides
        references to it (and the target is actually set).
        """
        opts = {}
        return self.field.storage()
        targetx = targety = None
        if self.field.targetx_field:
            targetx = getattr(self.instance, self.field.targetx_field, None)
        if self.field.targety_field:
            targety = getattr(self.instance, self.field.targety_field, None)
        targetx = targetx if targetx is not None else 50
        targety = targety if targety is not None else 50
        if targetx != 50 or targety != 50:
            opts['target'] = (targetx, targety)
        return opts

    def __getitem__(self, key):
        app_name = self.instance._meta.app_label if self.instance else None
        opts = aliases.get(key, app_name=app_name)
        if not opts:
            raise IndexError
        return EasyImage(self, opts=opts)


class EasyImageField(ImageField):
    attr_class = EasyImageFieldFile

    def __init__(self, *args, **kwargs):
        # Arguments not explicitly defined so that the normal ImageField
        # positional arguments can be used.
        self.targetx_field = kwargs.pop('targetx_field', None)
        self.targety_field = kwargs.pop('targety_field', None)
        super(EasyImageField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(EasyImageField, self).deconstruct()
        if self.targetx_field:
            kwargs["targetx_field"] = self.targetx_field
        if self.targety_field:
            kwargs["targety_field"] = self.targety_field
        return name, path, args, kwargs
