from easy_images.engine.base import BaseEngine

from .generator import PILGenerator


class Engine(PILGenerator, BaseEngine):
    pass
