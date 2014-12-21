from easy_images.engine.base import BaseEngine
from easy_images.engine.queue.easy_images_db_queue import (
    DBQueue,
    DBCachedQueue,
)

from .generator import PILGenerator


class Engine(PILGenerator, BaseEngine):
    pass


class DBQueueEngine(DBQueue, Engine):
    pass


class DBCachedQueueEngine(DBCachedQueue, Engine):
    pass
