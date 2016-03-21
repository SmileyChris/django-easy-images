from unittest import TestCase

import mock

from . import library


class AliasesTest(TestCase):

    def setUp(self):
        self.real_settings = library.settings
        library.settings = mock.Mock(spec=['EASY_IMAGES__ALIASES'])
        self.aliases_setting = mock.PropertyMock(return_value={})
        type(library.settings).EASY_IMAGES__ALIASES = self.aliases_setting

    def tearDown(self):
        library.settings = self.real_settings

    def test_settings_empty(self):
        aliases = library.Aliases()
        self.assertEqual(aliases.all(), {})
        self.assertTrue(self.aliases_setting.called)

    def test_settings_basic(self):
        ALIASES = {
            'small': {'crop': (48, 48)}, 'tiny': {'crop': (16, 16)}}
        self.aliases_setting.return_value = ALIASES
        aliases = library.Aliases()
        self.assertEqual(aliases.all(), ALIASES)
        self.assertTrue(self.aliases_setting.called)

    def test_settings_app(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)},
            'tiny': {'crop': (16, 16)},
            'some_app:small': {'crop': (32, 32)}
        }
        aliases = library.Aliases()
        self.assertEqual(
            aliases.all(), {
                'small': {'crop': (48, 48)},
                'tiny': {'crop': (16, 16)},
            })
        self.assertEqual(
            aliases.all(app_name='some_app'), {'small': {'crop': (32, 32)}})
        self.assertEqual(aliases.all(app_name='other_app'), {})

    def test_get(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)}, 'tiny': {'crop': (16, 16)}}
        aliases = library.Aliases()
        self.assertEqual(
            aliases.get('tiny'), {'ALIAS': 'tiny', 'crop': (16, 16)})

    def test_get_no_match(self):
        self.aliases_setting.return_value = {'small': {'crop': (48, 48)}}
        aliases = library.Aliases()
        self.assertEqual(aliases.get('tiny'), None)

    def test_get_app_bad(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)}, 'tiny': {'crop': (16, 16)}}
        aliases = library.Aliases()
        self.assertEqual(
            aliases.get('tiny', app_name='other_app'),
            {'ALIAS': 'tiny', 'crop': (16, 16)})

    def test_get_app(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)},
            'tiny': {'crop': (16, 16)},
            'some_app:small': {'crop': (32, 32)}
        }
        aliases = library.Aliases()
        self.assertEqual(
            aliases.get('small', app_name='some_app'),
            {'crop': (32, 32), 'ALIAS': 'small', 'ALIAS_APP_NAME': 'some_app'})

    def test_get_app_fallback(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)},
            'tiny': {'crop': (16, 16)},
            'some_app:small': {'crop': (32, 32)}
        }
        aliases = library.Aliases()
        self.assertEqual(
            aliases.get('tiny', app_name='some_app'),
            {'crop': (16, 16), 'ALIAS': 'tiny'})

    def test_get_app_no_match(self):
        self.aliases_setting.return_value = {
            'small': {'crop': (48, 48)},
            'tiny': {'crop': (16, 16)},
            'some_app:small': {'crop': (32, 32)}
        }
        aliases = library.Aliases()
        self.assertEqual(aliases.get('huge', app_name='some_app'), None)

    def test_map(self):
        aliases = library.Aliases()
        aliases.get = mock.Mock(
            side_effect=[{'crop': (16, 16)}, {'crop': (32, 32)}])
        output = aliases.map('test', 'test2')
        self.assertEqual(
            output, {'test': {'crop': (16, 16)}, 'test2': {'crop': (32, 32)}})

    def test_map_prefix(self):
        aliases = library.Aliases()
        aliases.get = mock.Mock(
            side_effect=[{'crop': (16, 16)}, {'crop': (32, 32)}])
        output = aliases.map('test', 'test2', prefix='X-')
        self.assertEqual(
            output,
            {'X-test': {'crop': (16, 16)}, 'X-test2': {'crop': (32, 32)}})
