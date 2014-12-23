from easy_images.engine.base import BaseEngine
from easy_images.engine.queue.easy_images_db_queue import (
    DBQueue,
    CachedDBQueue,
)

from .generator import PILGenerator


class Engine(PILGenerator, BaseEngine):
    pass


class DBQueueEngine(DBQueue, Engine):
    pass


class CachedDBQueueEngine(CachedDBQueue, Engine):
    pass
