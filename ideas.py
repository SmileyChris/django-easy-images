import abc
import re
from abc import ABC
from typing import TypedDict

from numpy import source


class OptionError(Exception):
    pass


class Option:
    def __init__(self, key: str | None = None):
        if not key:
            key = self.get_key()
        assert key
        self.key = key

    def get_key(self):
        name = self.__class__.__name__
        if name.endswith('Option'):
            return name[:-6]
        return name.lower()
    
    def get_value(self, value: str):
        return value
    

class BooleanOption(Option):
    def get_value(self, value: str):
        if value.lower() in ('false', 'no', 'off', '0'):
            return False
        if value.lower() in ('', 'true', 'yes', 'on', '1'):
            return True
        raise OptionError(f'Invalid value for {self.get_key()}: {value}')
    

class SizeOption(Option):
    def get_value(self, value: str):
        match = re.match(r'^(\d+)[,x](\d)$', value, re.IGNORECASE)
        if not match:
            raise OptionError(f'Invalid value for {self.get_key()}: {value}')
        return (int(match.group(1)), int(match.group(2)))


class SourceOptions(TypedDict):
    storage: str
    name: str
    width: int
    height: int
    alpha: bool
    format: str


class State(TypedDict):
    img: FieldFile | None
    opts: SourceOptions


class CheckState(TypedDict):
    source: State
    current_opts: SourceOptions


class RunState(TypedDict):
    source: State
    current: State


class Filter(ABC):
    options: list[Option] = []
    requires_path = False
    requires_source_to_check = True

    @abc.abstractmethod
    def check(self, state: CheckState, options: dict) -> bool | SourceOptions:
        raise NotImplementedError

    @abc.abstractmethod
    def run(self, img, options: dict):
        raise NotImplementedError


class OptimizeFilter(Filter):
    options = [BooleanOption('optimize')]
    requires_path = False
    requires_source_to_check = False

    def check(self, state: State, options: dict) -> bool:
        return options.get('optimize', False)

    def run(self, img, options: dict):
        return options
    

class SourceLedgerManager(models.Manager):
    def from_file(self, file: FieldFile):
        storage = file.storage.name
        name = file.name


class SourceLedger(models.Model):
    storage = models.CharField(max_length=512)
    name = models.CharField(max_length=512)
    opts = models.JSONField()

    options = SourceLedgerManager()


from django.core.files.storage import storages



def pick_image_storage(instance, filename):
    check_storages = ['image']
    if instance.storage:
        if image_storage_name := instance.storage.opts.get('image_storage_name'):
            if image_storage_name not in check_storages:
                check_storages.insert(0, image_storage_name)
    for storage_name in check_storages:
        if storage_name in storages:
            return storages[storage_name]
    return storages['default']


class ProcessedLedger(models.Model):
    id = models.UUIDField(primary_key=True.uuid4, editable=False)
    source = models.ForeignKey(SourceLedger, on_delete=models.CASCADE)
    img = models.ImageField(
        storage=pick_image_storage,
        height_field='img_height',
        width_field='img_width',
    )
    img_height = models.IntegerField()
    img_width = models.IntegerField()



IMAGE_ALIASES = {
    'save': 'optimize size=1024x768',
    'save:webp': 'size=1920x1080',
}

"""
{{ report.image|image:"square_thumb" }}
{% image report.image 100x100 optimize %}

Fallback options if not generated yet:
 - source url (with checked option size if possible)
 - placeholder image


Batch lookup / generate for efficiency?

ImageQueue for processing images
"""

def get_options_from_alias(alias: str):
    if alias in IMAGE_ALIASES:
        return IMAGE_ALIASES[alias]
    return alias


class QueuedImage(TypedDict):
    file: FieldFile
    height: int
    width: int


def get_image(file: FieldFile, options) -> ProcessedLedger:
    ledger