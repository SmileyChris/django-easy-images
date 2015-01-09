from unittest import TestCase

from easy_images.engine.pil import Engine

from .. import engine, queue


class EngineTest(TestCase):

    def test_db_queue(self):
        self.assertTrue(issubclass(engine.DBQueueEngine, Engine))
        self.assertTrue(issubclass(engine.DBQueueEngine, queue.DBQueue))

    def test_cached_db_queue(self):
        self.assertTrue(issubclass(engine.CachedDBQueueEngine, Engine))
        self.assertTrue(
            issubclass(engine.CachedDBQueueEngine, queue.CachedDBQueue))
