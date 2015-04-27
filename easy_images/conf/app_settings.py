from django.conf import settings as django_settings


class AppSettings(object):
    """
    A holder for app-specific default settings (project settings have
    priority).

    Settings split with two underscores are looked up from project settings
    as a dictionary, for example::

        # In myapp.conf:
        class Settings(AppSettings):
            MYAPP__TASTE = 'sour'
            MYAPP__SCENT = 'apple'

        # In settings:
        MYAPP = {
            'TASTE': 'sweet',
        }

    Individual attributes can be retrieved, or entire underscored
    dictionaries::

        from myapp.conf import settings
        print("Tastes {0}".format(settings.MYAPP__TASTE))
        myapp_settings = settings.MYAPP
        print("Smells like {0}".format(myapp_settings['SCENT']))
    """

    def __getattribute__(self, attr):
        # Retrieve (or build) any settings dictionaries (split by two
        # undescores).
        try:
            dicts = super(AppSettings, self).__getattribute__('_app_dicts')
        except AttributeError:
            dicts = []
            for key in dir(self):
                if not key.startswith('_') and '__' in key:
                    potential_dict = key.split('__', 1)[0]
                    if potential_dict.upper():
                        dicts.append(potential_dict)
            self._app_dicts = dicts

        # If we're trying to get a settings dictionary, build and return it.
        if attr in dicts:
            dict_prefix = attr + '__'
            settings_dict = getattr(django_settings, attr, {}).copy()
            for full_key in dir(self):
                if not full_key.startswith(dict_prefix):
                    continue
                key = full_key[len(dict_prefix):]
                if key in settings_dict:
                    continue
                settings_dict[key] = super(AppSettings, self).__getattribute__(
                    full_key)
            return settings_dict

        # If it's a dictionary attribute we're looking for, retrieve it.
        dict_attr = (
            not attr.startswith('_')
            and '__' in attr
            and attr.split('__', 1)[0]
        )
        if dict_attr:
            try:
                settings_dict = getattr(django_settings, dict_attr)
                dict_prefix = dict_attr and dict_attr + '__'
                return settings_dict[attr[len(dict_prefix):]]
            except (AttributeError, KeyError):
                return super(AppSettings, self).__getattribute__(attr)

        # It must be just a standard attribute.
        try:
            # If it's not upper case then it's just an attribute of this class.
            if attr != attr.upper() and not dict_attr:
                raise AttributeError()
            return getattr(django_settings, attr)
        except AttributeError:
            return super(AppSettings, self).__getattribute__(attr)
