import mock
from unittest import TestCase

from . import app_settings


class Settings(app_settings.AppSettings):

    APPLE = 'apple'
    banana = 'BANANA'
    CHOCOLATE = 'no'
    COUNTRY__NAME = 'New Zealand'
    COUNTRY__CODE = 'NZ'


class AppSettingsTest(TestCase):

    def setUp(self):
        self.patcher = mock.patch.object(
            app_settings, 'django_settings', mock.NonCallableMagicMock,
            spec=[])
        django_settings = self.patcher.start()
        django_settings.FISH = 1
        django_settings.fish = 2
        django_settings.CHOCOLATE = 'yes'
        django_settings.COUNTRY = {'NAME': 'Middle Earth', 'ANIMAL': 'kiwi'}
        self.settings = Settings()

    def tearDown(self):
        self.patcher.stop()

    def test_passthrough(self):
        self.assertEqual(self.settings.FISH, 1)
        with self.assertRaises(AttributeError):
            self.settings.fish

    def test_local(self):
        self.assertEqual(self.settings.APPLE, 'apple')
        self.assertEqual(self.settings.banana, 'BANANA')

    def test_override(self):
        self.assertEqual(self.settings.CHOCOLATE, 'yes')

    def test_dict_attr(self):
        self.assertEqual(self.settings.COUNTRY__CODE, 'NZ')
        self.assertEqual(self.settings.COUNTRY__NAME, 'Middle Earth')
        self.assertEqual(self.settings.COUNTRY__ANIMAL, 'kiwi')
        with self.assertRaises(AttributeError):
            self.settings.COUNTRY__SNAKES

    def test_dict(self):
        self.assertEqual(
            self.settings.COUNTRY,
            {'CODE': 'NZ', 'NAME': 'Middle Earth', 'ANIMAL': 'kiwi'})
