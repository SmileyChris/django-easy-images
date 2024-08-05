from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from easy_images.management.process_queue import process_queue
from easy_images.models import EasyImage, ImageStatus


class Command(BaseCommand):
    help = "Process EasyImages that need to be built"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Force build images already generating"
        )
        parser.add_argument(
            "--retry",
            type=int,
            help="Retry builds with errors with no more than this many failures",
        )
        parser.add_argument(
            "--count-only",
            action="store_true",
            help=(
                "Just return a count the number of EasyImages that need to be" " built"
            ),
        )

    def handle(self, *, verbosity, retry=None, force=None, count_only=False, **options):
        if count_only:
            count = EasyImage.objects.filter(image="").count()
            self.stdout.write(f"{count} <img> thumbnails need building")
            counts = EasyImage.objects.filter(image="").aggregate(
                building=Count("pk", filter=Q(status=ImageStatus.BUILDING)),
                source_errors=Count("pk", filter=Q(status=ImageStatus.SOURCE_ERROR)),
                build_errors=Count("pk", filter=Q(status=ImageStatus.BUILD_ERROR)),
            )
            if any(counts.values()):
                self.stdout.write("of which:")
                if counts["building"]:
                    self.stdout.write(
                        f"  {counts['building']} marked as already building"
                    )
                if counts["source_errors"]:
                    self.stdout.write(f"  {counts['source_errors']} had source errors")
                if counts["build_errors"]:
                    self.stdout.write(f"  {counts['build_errors']} had build errors")
            return
        if verbosity:
            self.stdout.write("Building queued <img> thumbnails...")
        if not force and verbosity:
            counts = EasyImage.objects.filter(image="").aggregate(
                building=Count("pk", filter=Q(status=ImageStatus.BUILDING)),
                source_errors=Count("pk", filter=Q(status=ImageStatus.SOURCE_ERROR)),
                build_errors=Count("pk", filter=Q(status=ImageStatus.BUILD_ERROR)),
            )
            if retry:
                if retry:
                    retry_counts = EasyImage.objects.filter(
                        image="", error_count__lte=retry
                    ).aggregate(
                        source_errors=Count(
                            "pk", filter=Q(status=ImageStatus.SOURCE_ERROR)
                        ),
                        build_errors=Count(
                            "pk", filter=Q(status=ImageStatus.BUILD_ERROR)
                        ),
                    )
            if counts["building"]:
                self.stdout.write(
                    f"Skipping {counts['building']} marked as already building..."
                )
            if counts["source_errors"]:
                if retry:
                    skip = counts["source_errors"] - retry_counts["source_errors"]
                    if skip:
                        self.stdout.write(
                            f"Retrying {retry_counts['source_errors']} with source errors ({skip} with more than {retry} retries skipped)..."
                        )
                    else:
                        self.stdout.write(
                            f"Retrying {retry_counts['source_errors']} with source errors..."
                        )
                else:
                    self.stdout.write(
                        f"Skipping {counts['source_errors']} with source errors..."
                    )
            if counts["build_errors"]:
                if retry:
                    skip = counts["build_errors"] - retry_counts["build_errors"]
                    if skip:
                        self.stdout.write(
                            f"Retrying {retry_counts['build_errors']} with build errors ({skip} with more than {retry} retries skipped)..."
                        )
                    else:
                        self.stdout.write(
                            f"Retrying {retry_counts['build_errors']} with build errors..."
                        )
                else:
                    self.stdout.write(
                        f"Skipping {counts['build_errors']} with build errors..."
                    )
        if verbosity:
            self.stdout.flush()
        built = process_queue(force=bool(force), retry=retry, verbose=verbosity > 1)
        if built is None:
            if verbosity:
                self.stdout.write("No <img> thumbnails required building")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Built {built} <img> thumbnail{'' if built == 1 else 's'}"
            )
        )
