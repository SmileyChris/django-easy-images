from django.core.management.base import BaseCommand

from easy_images.management.process_queue import process_queue
from easy_images.models import EasyImage


class Command(BaseCommand):
    help = "Process EasyImages that need to be built"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Force build images already generating"
        )
        parser.add_argument(
            "--count-only",
            action="store_true",
            help=(
                "Just return a count the number of EasyImages that need to be" " built"
            ),
        )

    def handle(self, *, verbosity, force=None, count_only=False, **options):
        if count_only:
            count = EasyImage.objects.filter(image="").count()
            self.stdout.write(f"{count} <img> thumbnails need building")
            return
        if verbosity:
            self.stdout.write("Building queued <img> thumbnails...")
        if not force and verbosity:
            skipping = (
                EasyImage.objects.exclude(started_generating=None)
                .filter(image="")
                .count()
            )
            if skipping:
                self.stdout.write(f"Skipping {skipping} marked as being generated")
        if verbosity:
            self.stdout.flush()
        built = process_queue(force=bool(force))
        if not built:
            if verbosity:
                self.stdout.write("No <img> thumbnails required building")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully built {built} <img>"
                f" thumbnail{'' if built == 1 else 's'}"
            )
        )
