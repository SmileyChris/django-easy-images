from django.db.models import Q
from tqdm import tqdm

from easy_images.models import EasyImage, ImageStatus


def process_queue(force=False, retry: int | None = None):
    """
    Process the image queue, building images that need building.

    :param bool force: Force building images, even those that are marked as already building
        or that had errors
    :param int retry: Also retry images with errors with no more than this many failures
    """
    easy_images = EasyImage.objects.filter(image="")
    if not force:
        queued = Q(status=ImageStatus.QUEUED)
        if retry:
            retry_errors = Q(
                error_count__lte=retry,
                status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR],
            )
            easy_images = easy_images.filter(queued | retry_errors)
        else:
            easy_images = easy_images.filter(queued)

    built = 0
    for easy_image in tqdm(easy_images.iterator(), total=easy_images.count()):
        if easy_image.build(force=force):
            built += 1
    return built
