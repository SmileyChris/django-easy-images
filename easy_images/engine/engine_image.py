import abc


class BaseEngineImage(object):

    def __init__(self, image, opts):
        self.image = image
        self.opts = opts

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

    @abc.abstractmethod
    def bytes(self, options):
        """
        Image saved as an in-memory stream of bytes ready for saving to a file
        system.

        :rtype: BytesIO
        """
