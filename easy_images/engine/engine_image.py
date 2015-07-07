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
    def bytes(self, options):
        """
        Image saved as an in-memory stream of bytes ready for saving to a file
        system.

        :rtype: BytesIO
        """
