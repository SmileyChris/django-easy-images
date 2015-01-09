from unittest import TestCase
try:
    from io import BytesIO
except ImportError:  # pragma: no cover  Python 2/3 compatibility
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

from django.core.management import call_command
from django.core.management.base import CommandError
from easy_images.engine import default
import lockfile
import mock

from easy_images_db_queue import models
from easy_images_db_queue.management.commands.generate_images import Command


class GenerateImagesTest(TestCase):

    def setUp(self):
        self._lockfile_patch = mock.patch.object(lockfile, 'LockFile')
        self.lockfile_mock = self._lockfile_patch.__enter__()

    def tearDown(self):
        self._lockfile_patch.__exit__()

    def test_args(self):
        self.assertRaises(
            CommandError, call_command, 'generate_images', 'somearg')

    def test_none(self):
        with mock.patch.object(Command, 'get_engine'):
            call_command('generate_images')
            self.assertFalse(Command.get_engine.called)

    def test_actions(self):
        data_patch = mock.patch.object(
            models.Action, 'data', new_callable=mock.PropertyMock)
        pop_patch = mock.patch.object(models.Action.objects, 'pop')
        engine_patch = mock.patch.object(default, 'default_engine')
        data = [{'action': 1}, {'action': 2}]
        expected = [mock.call(action) for action in data]
        with pop_patch as mock_pop:
            mock_pop.side_effect = [models.Action, models.Action, None]
            with data_patch as mock_data:
                mock_data.side_effect = data
                with engine_patch as mock_engine:
                    call_command('generate_images')
                    self.assertEqual(mock_engine.generate.mock_calls, expected)

    def test_actions_custom_engine(self):
        data_patch = mock.patch.object(
            models.Action, 'data', new_callable=mock.PropertyMock)
        pop_patch = mock.patch.object(models.Action.objects, 'pop')
        engine_patch = mock.patch.object(default, 'default_engine')
        import_string_patch = mock.patch.object(default, 'import_string')
        data = [{'action': 1}, {'action': 2, 'engine': 'custom_engine'}]
        expected = [mock.call(action) for action in data]
        with pop_patch as mock_pop:
            mock_pop.side_effect = [models.Action, models.Action, None]
            with data_patch as mock_data:
                mock_data.side_effect = data
                with engine_patch as mock_engine:
                    with import_string_patch as mock_import_string:
                        call_command('generate_images')
                        self.assertEqual(
                            mock_engine.generate.mock_calls, expected[0:1])
                        mock_custom_engine = mock_import_string(
                            'custom_engine')()
                        self.assertEqual(
                            mock_custom_engine.generate.mock_calls,
                            expected[1:2])

    def test_lock(self):
        call_command('generate_images')
        self.assertTrue(self.lockfile_mock.called)
        self.assertTrue(self.lockfile_mock().acquire.called)
        self.assertTrue(self.lockfile_mock().release.called)

    def test_lock_locked(self):
        self.lockfile_mock().acquire.side_effect = lockfile.AlreadyLocked
        fake_stderr = BytesIO()
        self.assertRaises(
            SystemExit, call_command, 'generate_images', stderr=fake_stderr)

    def test_lock_locked_force(self):
        self.lockfile_mock().acquire.side_effect = [
            lockfile.AlreadyLocked, None]
        call_command('generate_images', force=True)
        self.assertTrue(self.lockfile_mock().break_lock.called)
        self.assertEqual(self.lockfile_mock().acquire.call_count, 2)
        self.assertTrue(self.lockfile_mock().release.called)

    def test_lock_locked_force_fail(self):
        self.lockfile_mock().acquire.side_effect = lockfile.AlreadyLocked
        fake_stderr = BytesIO()
        self.assertRaises(
            SystemExit, call_command, 'generate_images', stderr=fake_stderr,
            force=True)
