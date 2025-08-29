from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from easy_images.models import EasyImage, ImageStatus


@pytest.mark.django_db
def test_easy_images_status_empty():
    out = StringIO()
    call_command("easy_images", stdout=out)
    txt = out.getvalue()
    # Totals present and in order: source, generated, queued
    pos_source = txt.find("Total source images: 0")
    pos_generated = txt.find("Total generated images: 0")
    pos_queued = txt.find("Total images in queue: 0")
    assert pos_source != -1 and pos_generated != -1 and pos_queued != -1
    assert pos_source < pos_generated < pos_queued
    assert "Avg generated per source: 0.00" in txt
    assert "No images in queue" in txt


@pytest.mark.django_db
def test_easy_images_build_includes_stale_and_max_errors():
    now = timezone.now()

    # Queued image (should be processed)
    q1 = EasyImage.objects.create(args={}, name="q1")

    # BUILDING recent (should NOT be processed unless stale)
    b_recent = EasyImage.objects.create(
        status=ImageStatus.BUILDING,
        status_changed_date=now,
        args={},
        name="b_recent",
    )

    # BUILDING stale (should be processed with force=True)
    b_stale = EasyImage.objects.create(
        status=ImageStatus.BUILDING,
        status_changed_date=now - timedelta(seconds=1000),
        args={},
        name="b_stale",
    )

    # Errors within threshold (should be retried)
    err_ok = EasyImage.objects.create(
        status=ImageStatus.BUILD_ERROR,
        error_count=1,
        args={},
        name="err_ok",
    )

    # Errors above threshold (should be skipped)
    err_skip = EasyImage.objects.create(
        status=ImageStatus.SOURCE_ERROR,
        error_count=5,
        args={},
        name="err_skip",
    )

    out = StringIO()
    with mock.patch(
        "easy_images.models.EasyImage.build", autospec=True, return_value=True
    ) as mocked:
        # Use stale-after smaller than b_stale age, and max-errors=2
        call_command(
            "easy_images",
            "build",
            "--stale-after",
            "600",
            "--max-errors",
            "2",
            stdout=out,
        )

    # Should have processed q1, b_stale (forced), err_ok — not b_recent or err_skip
    processed_ids = {call.args[0].id for call in mocked.call_args_list}
    assert processed_ids == {q1.id, b_stale.id, err_ok.id}

    # Ensure stale was forced
    forced_flags = [
        call.kwargs.get("force", False)
        for call in mocked.call_args_list
        if call.args and call.args[0].id == b_stale.id
    ]
    assert any(forced_flags) and all(flag is True for flag in forced_flags)

    # Built summary present
    txt = out.getvalue()
    assert "Built 3 image" in txt


@pytest.mark.django_db
def test_easy_images_status_breakdown_and_stale_warning():
    now = timezone.now()
    EasyImage.objects.create(args={}, name="queued1")
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="building_recent", status_changed_date=now)
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="building_stale", status_changed_date=now - timedelta(seconds=1000))
    EasyImage.objects.create(status=ImageStatus.BUILD_ERROR, args={}, name="build_error")
    EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, args={}, name="source_error")
    # Add built thumbnails (3 total), two for the same source (srcA) and one for srcB
    EasyImage.objects.create(image="thumbs/a1.jpg", width=100, height=100, args={"width": 100}, name="srcA")
    EasyImage.objects.create(image="thumbs/a2.jpg", width=200, height=200, args={"width": 200}, name="srcA")
    EasyImage.objects.create(image="thumbs/b1.jpg", width=300, height=300, args={"width": 300}, name="srcB")

    out = StringIO()
    call_command("easy_images", "status", stdout=out)
    txt = out.getvalue()
    # Basic counts present and ordered totals: source, generated, queued
    # Distinct sources = 5 (above) + 2 (srcA, srcB)
    pos_source = txt.find("Total source images: 7")
    pos_generated = txt.find("Total generated images: 3")
    pos_queued = txt.find("Total images in queue: 5")
    assert pos_source != -1 and pos_generated != -1 and pos_queued != -1
    assert pos_source < pos_generated < pos_queued
    # 3 / 7 = 0.4286 -> 0.43
    assert "Avg generated per source: 0.43" in txt
    assert "Queued:" in txt
    assert "Building:" in txt
    assert "Build errors:" in txt or "Build error:" in txt
    assert "Source errors:" in txt or "Source error:" in txt
    # Stale warning mentioned
    assert "possibly stale" in txt


@pytest.mark.django_db
def test_easy_images_requeue_command_changes_statuses():
    now = timezone.now()
    # Errors
    e1 = EasyImage.objects.create(status=ImageStatus.BUILD_ERROR, error_count=1, args={}, name="e1")
    e2 = EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, error_count=3, args={}, name="e2")
    e3 = EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, error_count=10, args={}, name="e3")  # should be skipped with max-errors=5
    # Stale BUILDING
    b_stale = EasyImage.objects.create(status=ImageStatus.BUILDING, status_changed_date=now - timedelta(seconds=1000), args={}, name="b_stale")
    # Recent BUILDING (not stale)
    EasyImage.objects.create(status=ImageStatus.BUILDING, status_changed_date=now, args={}, name="b_recent")

    out = StringIO()
    call_command(
        "easy_images",
        "requeue",
        "--max-errors",
        "5",
        "--include-stale",
        "--stale-after",
        "600",
        stdout=out,
    )

    # Reload and check statuses
    for img in (e1, e2, b_stale):
        img.refresh_from_db()
        assert img.status == ImageStatus.QUEUED
    # e3 should remain in error due to high error_count
    e3.refresh_from_db()
    assert e3.status in (ImageStatus.SOURCE_ERROR, ImageStatus.BUILD_ERROR)
    # Output includes requeue count
    assert "Requeued" in out.getvalue() or "No images to requeue" in out.getvalue()


@pytest.mark.django_db
def test_easy_images_status_json_format():
    # Setup: 2 sources (A,B), 1 generated, 2 queued, 1 building stale, 1 source error
    now = timezone.now()
    EasyImage.objects.create(args={}, name="A")  # queued
    EasyImage.objects.create(args={}, name="B")  # queued
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="C", status_changed_date=now - timedelta(seconds=1000))
    EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, args={}, name="D")
    EasyImage.objects.create(image="thumbs/a1.jpg", width=100, height=100, args={"width": 100}, name="A")  # generated

    out = StringIO()
    call_command("easy_images", "status", "--format", "json", "--stale-after", "600", stdout=out)
    import json as _json
    data = _json.loads(out.getvalue())

    assert data["counts"]["sources"] == 4  # A,B,C,D
    assert data["counts"]["generated"] == 1
    # queued here means all unbuilt (includes queued/building/errors)
    assert data["counts"]["queued"] == 4
    assert data["counts"]["building"] == 1
    assert data["counts"]["source_errors"] == 1
    assert data["counts"]["build_errors"] == 0
    assert data["stale"]["threshold_seconds"] == 600
    assert data["stale"]["count"] == 1
    assert isinstance(data["error_dist"], list)
    # Suggestions should include build (stale) and requeue (errors)
    joined = "\n".join(data.get("suggestions", []))
    assert "easy_images build" in joined
    assert "easy_images requeue" in joined


@pytest.mark.django_db
def test_easy_images_status_pretty_summary_and_suggestions():
    now = timezone.now()
    # 2 sources; 1 generated; 1 queued; 1 building stale; 1 source error
    EasyImage.objects.create(args={}, name="A")  # queued
    EasyImage.objects.create(status=ImageStatus.BUILDING, args={}, name="B", status_changed_date=now - timedelta(seconds=1000))
    EasyImage.objects.create(status=ImageStatus.SOURCE_ERROR, args={"width": 1}, name="B")
    EasyImage.objects.create(image="thumbs/a1.jpg", width=100, height=100, args={"width": 100}, name="A")

    out = StringIO()
    call_command("easy_images", "status", "--format", "pretty", "--stale-after", "600", stdout=out)
    txt = out.getvalue()
    assert "Summary:" in txt
    # Check key numbers are present
    assert "2 sources" in txt
    assert "1 generated" in txt
    # queued here shows all unbuilt items
    assert "3 queued" in txt
    assert "1 building" in txt
    assert "1 stale" in txt
    assert "1 errors" in txt
    # Bars and suggestions present
    assert "Breakdown:" in txt
    assert "Suggestions:" in txt
    assert "easy_images build" in txt
    assert "easy_images requeue" in txt
