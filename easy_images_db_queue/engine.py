from easy_images.engine.pil.engine import Engine

from . import queue


class DBQueueEngine(queue.DBQueue, Engine):
    pass


class CachedDBQueueEngine(queue.CachedDBQueue, Engine):
    pass
