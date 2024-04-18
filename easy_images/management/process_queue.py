from tqdm import tqdm

from easy_images.models import EasyImage


def process_queue(force=False):
    easy_images = EasyImage.objects.filter(image="")
    if not force:
        easy_images = easy_images.filter(started_generating=None)

    built = 0
    for easy_image in tqdm(easy_images.iterator(), total=easy_images.count()):
        if easy_image.build(force=force):
            built += 1
    return built
