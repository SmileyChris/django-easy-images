import sys
import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from django.utils import timezone

from easy_images.management.process_queue import process_queue, requeue_images
from easy_images.models import EasyImage, ImageStatus


class Command(BaseCommand):
    help = "Manage EasyImage queue - build, requeue, or check status"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            dest="subcommand",
            help="Subcommand to run (defaults to 'status' if not specified)",
        )

        # Status subcommand (default)
        status_parser = subparsers.add_parser(
            "status", help="Show queue statistics (default action)"
        )
        status_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed breakdown by error type",
        )
        status_parser.add_argument(
            "--format",
            choices=["pretty", "plain", "json"],
            help="Output format (pretty on TTY, plain otherwise)",
        )
        status_parser.add_argument(
            "--stale-after",
            type=int,
            default=600,
            help="Consider BUILDING older than this many seconds as stale (default: 600)",
        )
        status_parser.add_argument(
            "--fail-on-stale",
            action="store_true",
            help="Exit with non-zero status if stale BUILDING images are detected",
        )
        status_parser.add_argument(
            "--fail-on-errors",
            type=int,
            help="Exit non-zero if total errors exceed this number",
        )

        # Build subcommand
        build_parser = subparsers.add_parser("build", help="Process queued images")
        build_parser.add_argument(
            "--stale-after",
            type=int,
            default=600,
            help="Consider images stuck in BUILDING for this many seconds as stale (default: 600)",
        )
        build_parser.add_argument(
            "--max-errors",
            type=int,
            help="Skip images with more than this many errors",
        )
        build_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed progress and errors",
        )

        # Requeue subcommand
        requeue_parser = subparsers.add_parser(
            "requeue", help="Reset failed images to QUEUED status"
        )
        requeue_parser.add_argument(
            "--max-errors",
            type=int,
            help="Only requeue images with at most this many errors",
        )
        requeue_parser.add_argument(
            "--include-stale",
            action="store_true",
            help="Also requeue images stuck in BUILDING status",
        )
        requeue_parser.add_argument(
            "--stale-after",
            type=int,
            default=600,
            help="Consider images stuck in BUILDING for this many seconds as stale (default: 600)",
        )

    def handle(self, *args, **options):
        subcommand = options.get("subcommand", "status")
        
        if not subcommand or subcommand == "status":
            self.handle_status(**options)
        elif subcommand == "build":
            self.handle_build(**options)
        elif subcommand == "requeue":
            self.handle_requeue(**options)
        else:
            raise CommandError(f"Unknown subcommand: {subcommand}")

    def handle_status(self, **options):
        verbose = options.get("verbose", False)
        fmt = options.get("format")
        stale_after = options.get("stale_after", 600)
        fail_on_stale = options.get("fail_on_stale", False)
        fail_on_errors = options.get("fail_on_errors")

        # Totals
        total = EasyImage.objects.filter(image="").count()
        total_generated = EasyImage.objects.exclude(image="").count()
        total_sources = EasyImage.objects.values("storage", "name").distinct().count()
        avg_generated_per_source = (
            (total_generated / total_sources) if total_sources else 0.0
        )

        # Status breakdown
        counts = EasyImage.objects.filter(image="").aggregate(
            queued=Count("pk", filter=Q(status=ImageStatus.QUEUED)),
            building=Count("pk", filter=Q(status=ImageStatus.BUILDING)),
            source_errors=Count("pk", filter=Q(status=ImageStatus.SOURCE_ERROR)),
            build_errors=Count("pk", filter=Q(status=ImageStatus.BUILD_ERROR)),
        )
        stale_threshold = timezone.now() - timedelta(seconds=stale_after)
        stale_count = EasyImage.objects.filter(
            image="",
            status=ImageStatus.BUILDING,
            status_changed_date__lt=stale_threshold,
        ).count()
        error_dist_qs = (
            EasyImage.objects.filter(
                image="",
                status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR],
            )
            .values("error_count")
            .annotate(count=Count("pk"))
            .order_by("error_count")
        )
        error_dist = list(error_dist_qs)
        total_errors = (counts["source_errors"] or 0) + (counts["build_errors"] or 0)

        # Suggestions
        suggestions: list[str] = []
        if stale_count:
            suggestions.append(
                f"python manage.py easy_images build --stale-after {stale_after}"
            )
        if total_errors:
            suggestions.append("python manage.py easy_images requeue --max-errors 3")
        if (counts["queued"] or 0) and not (counts["building"] or 0):
            suggestions.append("python manage.py easy_images build")

        # Determine output format
        out_stream = self.stdout
        is_tty = getattr(out_stream, "isatty", lambda: False)()
        if not fmt:
            fmt = "pretty" if is_tty else "plain"

        data = {
            "counts": {
                "sources": total_sources,
                "generated": total_generated,
                "queued": total,
                "building": counts["building"] or 0,
                "source_errors": counts["source_errors"] or 0,
                "build_errors": counts["build_errors"] or 0,
            },
            "avg_per_source": avg_generated_per_source,
            "stale": {"threshold_seconds": stale_after, "count": stale_count},
            "error_dist": error_dist,
            "suggestions": suggestions,
        }

        if fmt == "json":
            out_stream.write(json.dumps(data))
        elif fmt == "plain":
            # Totals (source, generated, queued)
            out_stream.write(f"Total source images: {total_sources}\n")
            out_stream.write(f"Total generated images: {total_generated}\n")
            out_stream.write(f"Total images in queue: {total}\n")
            out_stream.write(
                f"Avg generated per source: {avg_generated_per_source:.2f}\n"
            )
            if total == 0:
                out_stream.write("No images in queue\n")
            else:
                out_stream.write("\nStatus breakdown:\n")
                if counts["queued"]:
                    out_stream.write(f"  Queued: {counts['queued']}\n")
                if counts["building"]:
                    out_stream.write(f"  Building: {counts['building']}\n")
                    if stale_count:
                        out_stream.write(
                            self.style.WARNING(
                                f"    ({stale_count} possibly stale > {stale_after}s)\n"
                            )
                        )
                if counts["source_errors"]:
                    out_stream.write(
                        self.style.ERROR(
                            f"  Source errors: {counts['source_errors']}\n"
                        )
                    )
                if counts["build_errors"]:
                    out_stream.write(
                        self.style.ERROR(
                            f"  Build errors: {counts['build_errors']}\n"
                        )
                    )
                if verbose and total_errors:
                    out_stream.write("\nError count distribution:\n")
                    for dist in error_dist:
                        out_stream.write(
                            f"  {dist['error_count']} error(s): {dist['count']} images\n"
                        )
                if suggestions:
                    out_stream.write("\nSuggestions:\n  " + "\n  ".join(suggestions) + "\n")
        else:  # pretty
            # One-line summary
            summary = (
                f"{total_sources} sources | {total_generated} generated "
                f"({avg_generated_per_source:.2f}/src) | {total} queued | "
                f"{counts['building'] or 0} building"
            )
            if stale_count:
                summary += f" ({stale_count} stale)"
            summary += (
                f" | {total_errors} errors (S:{counts['source_errors'] or 0} "
                f"B:{counts['build_errors'] or 0})"
            )
            out_stream.write(self.style.MIGRATE_HEADING("Summary: ") + summary + "\n")

            # Bars
            def bar(n: int, max_n: int, width: int = 10) -> str:
                if max_n <= 0:
                    return ""
                filled = int(round((n / max_n) * width))
                return "█" * filled

            max_status = max(total or 0, counts["building"] or 0, total_errors or 0)
            if max_status == 0:
                max_status = 1
            out_stream.write("\nTotals:\n")
            out_stream.write(f"  Total source images: {total_sources}\n")
            out_stream.write(f"  Total generated images: {total_generated}\n")
            out_stream.write(f"  Total images in queue: {total}\n")
            out_stream.write(
                f"  Avg generated per source: {avg_generated_per_source:.2f}\n"
            )
            out_stream.write("\nBreakdown:\n")
            out_stream.write(
                f"  Queued:   {total:>4} {bar(total, max_status)}\n"
            )
            b_line = f"  Building: {counts['building'] or 0:>4} {bar(counts['building'] or 0, max_status)}"
            if stale_count:
                b_line += f"  ({stale_count} stale > {stale_after}s)"
            out_stream.write(b_line + "\n")
            out_stream.write(
                f"  Errors:   {total_errors:>4} {bar(total_errors, max_status)} "
                f"(source: {counts['source_errors'] or 0}, build: {counts['build_errors'] or 0})\n"
            )
            if verbose and total_errors:
                out_stream.write("\nError count distribution:\n")
                for dist in error_dist:
                    out_stream.write(
                        f"  {dist['error_count']} error(s): {dist['count']} images\n"
                    )
            if suggestions:
                out_stream.write("\nSuggestions:\n  " + "\n  ".join(suggestions) + "\n")

        # Health gates
        should_fail = False
        if fail_on_stale and stale_count:
            should_fail = True
        if fail_on_errors is not None and total_errors > fail_on_errors:
            should_fail = True
        if should_fail:
            sys.exit(1)

    def handle_build(self, **options):
        stale_after = options.get("stale_after", 600)
        max_errors = options.get("max_errors")
        verbose = options.get("verbose", False)
        
        if verbose:
            self.stdout.write("Building queued images...")
            
            # Show what will be processed
            stale_threshold = timezone.now() - timedelta(seconds=stale_after)
            stale_count = EasyImage.objects.filter(
                image="",
                status=ImageStatus.BUILDING,
                status_changed_date__lt=stale_threshold
            ).count()
            
            if stale_count:
                self.stdout.write(
                    f"Including {stale_count} stale images (BUILDING > {stale_after}s)"
                )
            
            if max_errors is not None:
                error_count = EasyImage.objects.filter(
                    image="",
                    status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR],
                    error_count__lte=max_errors
                ).count()
                skip_count = EasyImage.objects.filter(
                    image="",
                    status__in=[ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR],
                    error_count__gt=max_errors
                ).count()
                
                if error_count:
                    self.stdout.write(f"Retrying {error_count} images with errors")
                if skip_count:
                    self.stdout.write(
                        f"Skipping {skip_count} images with > {max_errors} errors"
                    )
            
            self.stdout.flush()
        
        built = process_queue(
            stale_after_seconds=stale_after,
            max_errors=max_errors,
            verbose=verbose
        )
        
        if built is None:
            if verbose:
                self.stdout.write("No images required building")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Built {built} image{'' if built == 1 else 's'}"
                )
            )

    def handle_requeue(self, **options):
        max_errors = options.get("max_errors")
        include_stale = options.get("include_stale", False)
        stale_after = options.get("stale_after", 600)
        
        requeued = requeue_images(
            max_errors=max_errors,
            include_stale=include_stale,
            stale_after_seconds=stale_after if include_stale else None
        )
        
        if requeued == 0:
            self.stdout.write("No images to requeue")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Requeued {requeued} image{'' if requeued == 1 else 's'}"
                )
            )
