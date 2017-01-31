import abc


class BaseEngineImage(object):
    required_meta = ('size',)
    optional_meta = ('transparent', 'rotation', 'mirrored')

    def __init__(self, image, opts):
        self.image = image
        self.opts = opts

    def build_meta(self):
        meta = {}
        for attr in self.required_meta:
            meta[attr] = getattr(self, attr)
        for attr in self.optional_meta:
            value = getattr(self, attr)
            if value:
                meta[attr] = value
        return meta

    @property
    def size(self):
        """
        Return the image size as a two-part tuple, for example ``(64, 64)``.

        :rtype: tuple
        """
        return self.image.size

    @property
    def transparent(self):
        """
        Check whether the image is transparent.

        :rtype: boolean
        """
        return False

    @property
    def mode(self):
        """
        Return the image mode, for example 'RGBA'.
        """
        return self.image.mode

    @property
    def rotation(self):
        """
        Return the virtual rotation of this image.

        - 0 means no rotation
        - 1 means 90 degrees clockwise
        - 2 means 180 degrees rotation
        - 3 means 270 degrees clockwise (i.e. 90 degrees anticlockwise)

        :rtype: integer
        """
        orientation_to_rotation = {8: 1, 5: 1, 3: 2, 4: 2, 6: 3, 7: 3}
        return orientation_to_rotation.get(self.exif_orientation, 0)

    @property
    def mirrored(self):
        """
        Check whether this image is virtually horizontal mirrored.

        :rtype: boolean
        """
        return self.exif_orientation in (2, 5, 4, 7)

    @property
    def exif_orientation(self):
        return 1

    @abc.abstractmethod
    def bytes(self, filename):
        """
        Image saved as an in-memory stream of bytes ready for saving to a file
        system.

        :rtype: BytesIO
        """

    def new_engine_image(self, image):
        return self.__class__(image=image, opts=self.opts)

    def filter(self, filters):
        """
        Return an engine image processed through one or more optional filters.

        The class can define ``filter_[name]`` methods which take image and
        value parameters and return an internal image instance.

        :param filters: A list of (name, value) tuples.
        """
        image = self.image
        changed = False
        for name, value in filters:
            filter_method = getattr(self, 'filter_{}'.format(name), None)
            if callable(filter_method):
                new_image = filter_method(image, value)
                if new_image:
                    image = new_image
                    changed = True
        if not changed:
            return self
        return self.new_engine_image(image)

    @abc.abstractmethod
    def convert_mode(self, mode):
        """
        Return an engine image which hase the correct image mode.
        """

    @abc.abstractmethod
    def replace_alpha(self, color):
        """
        Return an engine image with the alpha layer replaced with a specific
        hex color.
        """

    @abc.abstractmethod
    def resize(self, size, antialias=True):
        """
        Return an engine image resized to the new dimensions.
        """

    @abc.abstractmethod
    def crop(self, box):
        """
        Return an engine image cropped to box dimensions ``(x, y, x2, y2)``.
        """

    @abc.abstractmethod
    def canvas(self, size):
        """
        Change the canvas size of an image (centering the original).
        """

    def smart_crop(self, size):
        """
        Automatically crop edges with least noise until size matches, or return
        the image unchanged if unneeded or not implemented.
        """
        return self

    def convert_color_profile(self):
        """
        Convert an image's embedded color profile to standard RGB,
        returning the modified image (or returning the image unchanged
        if unneeded or not implemented).
        """
