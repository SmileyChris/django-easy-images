from __future__ import unicode_literals
import abc

from .filename_info import FilenameInfo


class BaseLedger(object):
    filename_info_class = FilenameInfo
    filename = '{info.src_dir}{info.hash}{info.ext}'
    """
    The default file name format for generated images.

    See the :cls:`~easy_images.ledger.filename_info.FilenameInfo` class for the
    available properties.
    """
    highres_infix = '_{highres}x'
    """
    The infix used to distinguish images generated for high resolution
    displays.

    It is added to the filename just just before the '.' of the extension for
    images generated with the ``HIGHRES`` option.
    """

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

    def meta_list(self, sources, **kwargs):
        """
        Like :meth:`meta` but accepts multiple sources.

        :param sources: a list of (source_path, opts) tuple pairs.
        """
        return [self.meta(*args) for args in sources]

    def get_filename_info(self, source_path, opts, **kwargs):
        info = kwargs.get('filename_info')
        if info is not None:
            return info
        return self.filename_info_class(
            source_path=source_path, opts=opts, ledger=self, **kwargs)

    def build_filename(self, source_path, opts, **kwargs):
        """
        The filename for a source image, given a set of options.

        The format is looked up in the opts matching the ``FILENAME`` key,
        falling back to the default format coming from :attr:`filename`.
        """
        filename_fmt = opts.get('FILENAME') or self.filename
        info = self.get_filename_info(
            source_path=source_path, opts=opts, **kwargs)
        return filename_fmt.format(info=info)

    def output_extension(
            self, source_path, opts, source_ext, meta=None, **kwargs):
        """
        The generated filename extension (including the ``.``).
        """
        if meta is None:
            meta = self.meta(source_path, opts)
        if meta and meta.get('transparent'):
            return '.png'
        return '.jpg'

    @abc.abstractmethod
    def save(self, source_path, opts, meta, **kwargs):
        """
        Save the data.
        """

    # TODO: save_list?
