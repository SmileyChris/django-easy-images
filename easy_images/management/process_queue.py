import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from tqdm import tqdm

from easy_images.models import EasyImage, ImageStatus

logger = logging.getLogger(__name__)


def process_queue(
    force=False, 
    retry: int | None = None, 
    verbose=False,
    stale_after_seconds: int | None = None,
    max_errors: int | None = None
):
    """
    Process the image queue, building images that need building.

    :param bool force: Force building images, even those that are marked as already building
        or that had errors (deprecated, use stale_after_seconds instead)
    :param int retry: Also retry images with errors with no more than this many failures
        (deprecated, use max_errors instead)
    :param bool verbose: Show detailed progress and raise errors for debugging
    :param int stale_after_seconds: Consider BUILDING images older than this as stale
    :param int max_errors: Only process images with at most this many errors
    """
    # Handle deprecated parameters
    if retry is not None and max_errors is None:
        max_errors = retry
    
    easy_images = EasyImage.objects.filter(image="")
    
    if not force:
        # Start with queued images
        filters = Q(status=ImageStatus.QUEUED)
        
        # Add stale BUILDING images
        if stale_after_seconds:
            stale_threshold = timezone.now() - timedelta(seconds=stale_after_seconds)
            stale_building = Q(
                status=ImageStatus.BUILDING,
                status_changed_date__lt=stale_threshold
            )
            filters |= stale_building
        
        # Add error images within max_errors limit
        if max_errors is not None:
            retry_errors = Q(
                error_count__lte=max_errors,
                status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR],
            )
            filters |= retry_errors
        
        easy_images = easy_images.filter(filters)

    total = easy_images.count()
    if not total:
        return None

    built = 0
    for easy_image in tqdm(easy_images.iterator(), total=total):
        try:
            # Check if this is a stale build that needs force
            is_stale = (
                stale_after_seconds 
                and easy_image.status == ImageStatus.BUILDING
                and easy_image.status_changed_date
                and easy_image.status_changed_date < timezone.now() - timedelta(seconds=stale_after_seconds)
            )
            
            if easy_image.build(force=bool(force or is_stale), raise_error=verbose):
                built += 1
        except Exception:
            logger.exception(f"Error building {easy_image}")
    return built


def requeue_images(
    max_errors: int | None = None,
    include_stale: bool = False,
    stale_after_seconds: int | None = None
):
    """
    Reset failed images back to QUEUED status.
    
    :param int max_errors: Only requeue images with at most this many errors
    :param bool include_stale: Also requeue stale BUILDING images
    :param int stale_after_seconds: When include_stale=True, consider BUILDING 
        images older than this as stale
    :return: Number of images requeued
    """
    # Start with error statuses
    filters = Q(status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR])
    
    # Add max_errors filter
    if max_errors is not None:
        filters &= Q(error_count__lte=max_errors)
    
    # Add stale BUILDING images if requested
    if include_stale and stale_after_seconds:
        stale_threshold = timezone.now() - timedelta(seconds=stale_after_seconds)
        stale_building = Q(
            status=ImageStatus.BUILDING,
            status_changed_date__lt=stale_threshold
        )
        filters |= stale_building
    
    # Update all matching images to QUEUED
    updated = EasyImage.objects.filter(image="").filter(filters).update(
        status=ImageStatus.QUEUED,
        status_changed_date=timezone.now()
    )
    
    return updated
