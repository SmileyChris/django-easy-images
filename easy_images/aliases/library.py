from easy_images.conf import settings


class Aliases(object):
    """
    A container which stores and retrieves named easy-images options
    dictionaries.
    """

    def __init__(self):
        """
        Initialize the Aliases object.
        """
        self._aliases = {None: {}}
        self.populate_from_settings()

    def populate_from_settings(self):
        """
        Populate the aliases from the ``ALIASES`` setting.
        """
        settings_aliases = settings.EASY_IMAGES__ALIASES
        if settings_aliases:
            for alias, opts in settings_aliases.items():
                if ':' in alias:
                    app_name, alias = alias.split(':', 1)
                else:
                    app_name = None
                self.set(alias, opts, app_name=app_name)

    def set(self, alias, options, app_name=None):
        """
        Add an alias.

        :param alias: The name of the alias to add.
        :param options: The easy-images options dictonary for this alias
            (should include ``size``).
        :param app_name: Limit this alias to an application.
        """
        target_aliases = self._aliases.setdefault(app_name, {})
        target_aliases[alias] = options

    def get(self, alias, app_name=None):
        """
        Get a dictionary of aliased options.

        If no matching alias is found, returns ``None``. The options dictionary
        will contain an ``'ALIAS'`` key (and ``'ALIAS_APP_NAME'``, if it
        matched an app-specific alias).

        :param alias: The name of the aliased options.
        :param app_name: Look first for aliases for this specific application.
        :rtype: dict, None
        """
        opts = {'ALIAS': alias}
        if app_name:
            app_aliases = self._aliases.get(app_name, {})
            alias_opts = app_aliases.get(alias)
            if alias is not None:
                opts.update(alias_opts)
                opts['ALIAS_APP_NAME'] = app_name
        if 'ALIAS_APP_NAME' not in opts:
            alias_opts = self._aliases[None].get(alias)
            if alias_opts is None:
                return
            opts.update(alias_opts)
        return opts

    def all(self, app_name=None):
        """
        Get a dictionary of all aliases and their options.

        For example::

            >>> aliases.all()
            {'small': {'size': (100, 100)}, 'large': {'size': (400, 400)}}

        :param app_name: Get aliases for a specific application in addition to
            the standard ones.
        """
        if app_name not in self._aliases:
            return {}
        return self._aliases[app_name].copy()

    def map(self, *aliases, **kwargs):
        """
        Build a map of aliases; a dictionary where each key is the alias name
        and each value is an options dictionary.

        :param prefix: Prefix each map key with this string
        :param app_name: Look first for each alias in this specified
            application.

        .. seealso:: :func:`easy_images.images.annotate`
        """
        prefix = kwargs.get('prefix') or ''
        app_name = kwargs.get('app_name')
        opts_map = {}
        for alias in aliases:
            opts_map[prefix + alias] = self.get(alias, app_name=app_name)
        return opts_map
