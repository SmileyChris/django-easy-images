from optparse import make_option
import sys
import os.path
import tempfile

from django.core.management.base import BaseCommand, CommandError
import lockfile

from easy_images.engine import default
from easy_images.engine.queue.easy_images_db_queue import models


class Command(BaseCommand):
    help = "Generate queued images"
    option_list = BaseCommand.option_list + (
        make_option(
            '--lock',
            help="Fail silently if this lock has been taken by another "
            "process already."),
        make_option(
            '--force', action='store_true',
            help="Break any existing lock and acquire it for this process."),
    )

    def handle(self, *args, **options):
        if args:
            raise CommandError("No arguments expected")
        lock = self.get_lock(**options)
        try:
            while True:
                action_obj = models.Action.objects.pop()
                if not action_obj:
                    break
                engine = self.get_engine(action_obj.data)
                engine.generate(self)
        finally:
            lock.release()
        # TODO: some feedback unless low verbosity?

    def get_engine(self, action):
        engine_path = action.get('engine')
        if engine_path:
            return default.import_string(engine_path)()
        return default.default_engine

    def get_lock(self, **options):
        lock_path = options.get('lock') or 'easy_images'
        if not os.path.isabs(lock_path):
            lock_path = os.path.join(tempfile.gettempdir(), lock_path)
        lock = lockfile.LockFile(lock_path)
        try:
            lock.acquire(timeout=-1)
        except lockfile.AlreadyLocked:
            if options.get('force'):
                lock.break_lock()
                try:
                    lock.acquire(timeout=-1)
                except lockfile.AlreadyLocked:
                    sys.stderr.write(
                        "Could not establish lock even after breaking it.\n")
                    sys.exit(1)
            sys.stderr.write("Already locked, aborting.\n")
            sys.exit(0)
        return lock
