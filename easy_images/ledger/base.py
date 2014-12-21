from __future__ import unicode_literals
import datetime

from .filename_info import FilenameInfo


class BaseLedger(object):
    filename = '{info.src_dir}{info.hash}{info.ext}'
    """
    The default file name format for generated images.

    See the :cls:`~easy_images.ledger.filename_info.FilenameInfo` class for the
    available properties.
    """

    def exists(self, source_path, opts, **kwargs):
        """
        Whether the image with the provided opts has already been generated.

        The base behaviour assumes the image exists already.

        :rtype: boolean
        """
        return self.meta(source_path, opts) is not None

    def meta(self, source_path, opts, **kwargs):
        """
        The meta options for an image generated with the provided opts.

        For ungenerated images, ``None`` is returned, otherwise a dictionary
        will be returned (so an empty dictionary, although falsey, still
        indicates the image exists).

        Common meta options may be 'transparent', 'size', and 'date'.

        :rtype: dictionary, None
        """
        return {}

    def hash(self, source_path, opts, **kwargs):
        info = FilenameInfo(source_path=source_path, opts=opts, ledger=self)
        return info.hash

    def meta_list(self, sources, **kwargs):
        """
        Like :meth:`meta` but accepts multiple sources.

        :param sources: a list of (source_path, opts) tuple pairs.
        """
        return [self.meta(*args) for args in sources]

    def build_filename(self, source_path, opts, **kwargs):
        """
        The filename for a source image, given a set of options.

        The format is looked up in the opts matching the ``FILENAME`` key,
        falling back to the default format coming from :attr:`filename`.
        """
        filename_fmt = opts.get('FILENAME') or self.filename
        return filename_fmt.format(info=FilenameInfo(
            source_path=source_path, opts=opts, ledger=self, **kwargs))

    def output_extension(self, opts, source_ext, meta=None, **kwargs):
        """
        The generated filename extension (including the ``.``).
        """
        if meta is None:
            meta = self.meta(opts)
        if meta.get('transparent'):
            return '.png'
        return '.jpg'

    def save(self, source_path, opts, **kwargs):
        """
        Save the data.

        Needs to be implemented by a subclass.
        """
        raise NotImplementedError()

    # TODO: save_list?

    def build_meta(self, **kwargs):
        return {
            'date': datetime.datetime.utcnow().isoformat(),
        }.update(**kwargs)
