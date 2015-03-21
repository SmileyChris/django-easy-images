from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from easy_images.engine.default import default_engine
from easy_images.ledger.default import default_ledger


@python_2_unicode_compatible
class EasyImage(object):

    def __init__(self, source, opts, ledger=None, engine=None,
                 always_check_processing=True):
        self.source = source
        self.opts = opts
        self.ledger = ledger or default_ledger
        self.engine = engine or default_engine
        self.always_check_processing = always_check_processing

    def __str__(self):
        return self.url

    @property
    def name(self):
        """
        The filename for this image.
        """
        return self.ledger.build_filename(
            source_path=self.source_path, opts=self.opts, meta=self.meta)

    @property
    def hash(self):
        """
        A hash representing this combination of source image and options.
        """
        return self.ledger.get_filename_info(
            source_path=self.source_path, opts=self.opts).hash

    @property
    def processing(self):
        """
        Whether this image is currently being generated by the engine.

        :rtype: boolean
        """
        return self.engine.processing(self.hash)

    @property
    def exists(self):
        """
        Whether this image exists.

        If it is currently being generated, it is considered to *not* exist. To
        avoid this check, use ``self.meta is not None`` instead.

        :rtype: boolean
        """
        if self.always_check_processing or not hasattr(self, '_meta'):
            if self.processing:
                try:
                    del self.meta
                except AttributeError:
                    pass
                return False
        return self.meta is not None

    def build_url(self):
        """
        Build the URL without checking existance.
        """
        return self.engine.get_generated_storage(self.opts).url(self.name)

    @property
    def url(self):
        """
        The url if the image if it exists (or is generated in-process as part
        of this call) otherwise the "processing" url.

        Check if the image doesn't exist yet (and isn't currently being
        processed) an action to generate it is added to the engine.
        """
        processing = not self.generate()
        url = self.build_url()
        if processing:
            return self.engine.processing_url(
                source_path=self.source_path, opts=self.opts, source_url=url)
        return url

    @property
    def meta(self):
        """
        Any meta-data for this image.

        :rtype: dict, NoneType
        """
        if not hasattr(self, '_meta'):
            self._meta = self.ledger.meta(
                source_path=self.source_path, opts=self.opts)
        return self._meta

    @meta.setter
    def meta(self, value):
        self._meta = value

    @meta.deleter
    def meta(self):
        del self._meta

    @property
    def width(self):
        size = self.meta and self.meta.get('size')
        if size:
            return size[0]

    @property
    def height(self):
        size = self.meta and self.meta.get('size')
        if size:
            return size[1]

    def get_file(self):
        if not self.exists:
            return None
        return self.engine.get_generated(
            source_path=self.source_path, opts=self.opts)

    @property
    def source_path(self):
        try:
            return self.source.name
        except AttributeError:
            return '{0}'.format(self.source)

    def generate(self, force=False):
        """
        Generate the image.

        :param force: Force the generation, even if the image exists already.
        :returns: The image if generated in-process, or ``True`` if the image
            already exists.
        """
        if not force and self.exists:
            return True
        if 'KEY' in self.opts:
            opts = self.opts
        else:
            opts = {'KEY': self.hash}
            opts.update(self.opts)
        action = {
            'source': self.source_path, 'all_opts': {self.name: opts}}
        return self.engine.add(action)


class EasyImageBatch(object):
    """
    Interact with a ledger to more efficiently load multiple images in a single
    batch.

    Images loaded as part of a batch that aren't being generated will assume
    they are always available from that point on to avoid excessive "in
    generation" queries when iterating.
    """

    def __init__(self, sources=None, ledger=None, engine=None):
        """
        :param sources: An list of source & options tuple pairs to initialize
            this batch with.
        :param ledger: The ledger to use for batch-loading the images, and for
            creating ``EasyImage`` instances.
        :param engine: The engine to use when creating ``EasyImage`` instances.
        """
        self.loaded_images = []
        self.new_images = []
        self.ledger = ledger or default_ledger
        self.engine = engine or default_engine
        for source, opts in sources or ():
            self.add(source, opts)

    def add(self, source, opts):
        """
        Add image options to a batch that will be loaded in a single call.
        """
        image = EasyImage(
            source, opts, ledger=self.ledger, engine=self.engine,
            always_check_processing=False)
        self.new_images.append(image)
        return image

    def __iter__(self):
        """
        A generator that yields images, loading newly added images from the
        ledger in a single batch.
        """
        for image in self.loaded_images:
            yield image
        if self.new_images:
            loading_images, self.new_images = self.new_images, []
            # Exclude self.engine.processing_list items from meta_list.
            processing_list = self.engine.processing_list(
                image.hash for image in loading_images)
            meta_sources = []
            meta_images = []
            for image, processing in zip(loading_images, processing_list):
                if not processing:
                    meta_sources.append((image.source, image.opts))
                    meta_images.append(image)
            if meta_sources:
                meta_list = self.ledger.meta_list(meta_sources)
                for image, meta in zip(meta_images, meta_list):
                    image.meta = meta
            for image in loading_images:
                yield image
                self.loaded_images.append(image)

    def load(self):
        """
        Explicitly load any pending images in a single batch.

        Usually this isn't necessary - iterating the ``EasyImageBatch`` will
        have the same effect.
        """
        count = len(self.new_images)
        if count:
            list(self)
        return count

    def generate(self, force=False):
        """
        Add batched actions to generate all images that don't exist and aren't
        already being processed.

        :param force: Force the generation, even if images exist already (or
            are being processed).
        """
        self.load()
        images = list(self)
        if force:
            processing_list = images
        else:
            processing_list = self.engine.processing_list(
                image.hash for image in images)
        actions = {}
        for image, processing in zip(images, processing_list):
            if not force:
                if processing or image.meta is not None:
                    continue
            all_opts = actions.setdefault(image.source_path, [])
            all_opts.append(image.opts)
        for source_path, all_opts in six.iteritems(actions):
            self.engine.add({'source': source_path, 'all_opts': all_opts})


def annotate(obj_list, opts_map, get_source, batch=None):
    if not callable(get_source):
        source_attr = get_source
        get_source = lambda obj: getattr(obj, source_attr)

    generate = batch is None
    if generate:
        batch = EasyImageBatch()

    for obj in obj_list:
        for new_attr, opts in six.iteritems(opts_map):
            image = batch.add(get_source(obj), opts)
            setattr(obj, new_attr, image)

    if generate:
        return batch.generate()
