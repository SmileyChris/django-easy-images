from __future__ import unicode_literals
import base64
import hashlib
import posixpath


class FilenameInfo(object):

    def __init__(self, source_path, opts, ledger, **kwargs):
        self._source_path = source_path
        self._opts = opts
        self._ledger = ledger
        self._kwargs = kwargs

    def make_hash(self, text):
        return base64.urlsafe_b64encode(
            hashlib.sha1(text).digest()).rstrip('=')

    @property
    def src_dir(self):
        """
        The relative directory of the source image.

        If not blank, will include a trailing slash.
        """
        src_dir = posixpath.dirname(self._source_path)
        if not src_dir:
            return ''
        return src_dir + '/'

    @property
    def src_hash(self):
        """
        A 28 character url-safe base64 hash of the source image directory and
        name.
        """
        return self.make_hash(self._source_path)

    @property
    def opts(self):
        """
        A text representation of the options dictionary, sorted and underscore
        separated. Values of ``True`` are represented as just the key, values
        of ``None`` or ``False`` are dropped, all other values are separated
        with a dash.
        """
        if not hasattr(self, '_cached_opts'):
            parts = []
            for key, value in sorted(self._opts.items()):
                if key == key.upper() or value is False or value is None:
                    continue
                if value is True:
                    parts.append(key)
                else:
                    if isinstance(value, (list, tuple)):
                        value = ','.join('%s' % bit for bit in value)
                    parts.append('{key}-{value}'.format(key=key, value=value))
            self._cached_opts = '_'.join(parts)
        return self._cached_opts

    @opts.setter
    def opts(self, value):
        self._opts = value
        try:
            del self._cached_opts
        except AttributeError:
            pass

    @property
    def opts_hash(self):
        """
        A 28 character url-safe base64 hash of the options dictionary.
        """
        return self.make_hash(self.opts)

    @property
    def hash(self):
        """
        A 28 character url-safe base64 hash of the source image directory, name
        and options combined (source path and options combined with a ``':'``).
        """
        return self.make_hash('{0}:{1}'.format(
            self._source_path, self.opts))

    @property
    def src_name(self):
        """
        The base filename of the source image (excluding extension).
        """
        return posixpath.basename(self._source_path)

    @property
    def src_ext(self):
        """
        The file extension of the source image (including the '.').
        """
        return posixpath.splitext(self._source_path)[1]

    @property
    def ext(self):
        """
        The file extension of the processed image (including the '.').

        If the ``HIGHRES`` option is set, this will be prefixed with
        :attr:`~easy_images.ledger.base.Ledger.highres_infix`.
        """
        if not hasattr(self, '_cached_ext'):
            self._cached_ext = self._ledger.output_extension(
                source_path=self._source_path, opts=self._opts,
                source_ext=self.src_ext, **self._kwargs)
            highres = self._opts.get('HIGHRES')
            if highres:
                infix = self._ledger.highres_infix.format(highres=highres)
                self._cached_ext = infix + self._cached_ext
        return self._cached_ext

    @property
    def unique_ext(self):
        """
        The file extension of the processed image, unless it's the same as the
        source extension (in which case, returns ``''``).
        """
        if self.ext == self.src_ext:
            return ''
        return self.ext
