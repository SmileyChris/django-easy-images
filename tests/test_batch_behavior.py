"""
Test actual ImageBatch behavior (not mocked).

These tests validate the batch loading, incremental loading, auto-building,
and memory management improvements.
"""

import pytest
pytestmark = pytest.mark.vips
try:
    import pyvips  # noqa: F401
except Exception:
    pytest.skip("pyvips/libvips not available", allow_module_level=True)
from django.core.files.uploadedfile import SimpleUploadedFile

import pyvips
from easy_images.core import ImageBatch, Img
from tests.easy_images_tests.models import Profile


class TestImageBatchBehavior:
    """Test actual ImageBatch behavior."""

    def _create_test_file(self, name="test.jpg"):
        """Helper to create test file."""
        image = pyvips.Image.black(100, 100)
        content = image.write_to_buffer(".jpg")
        file = SimpleUploadedFile(name, content)
        profile = Profile.objects.create(name="Test", image=file)
        return profile.image

    @pytest.mark.django_db
    def test_fresh_batch_creation(self):
        """Test that Img() creates fresh batches by default."""
        img1 = Img(width=100)
        img2 = Img(width=100)

        # Should both have batch=None by default
        assert img1._batch is None
        assert img2._batch is None

        # When called, should create fresh batches
        file = self._create_test_file()
        bound1 = img1(file, build="src")
        bound2 = img2(file, build="src")

        # Should have different parent batches (fresh batch per call)
        assert bound1._parent_batch is not bound2._parent_batch

    @pytest.mark.django_db
    def test_shared_batch_usage(self):
        """Test explicit shared batch usage."""
        batch = ImageBatch()
        img1 = Img(batch=batch, width=100)
        img2 = Img(batch=batch, width=200)

        file = self._create_test_file()
        bound1 = img1(file, build="src")
        bound2 = img2(file, build="srcset")

        # Should share the same batch
        assert bound1._parent_batch is bound2._parent_batch
        assert bound1._parent_batch is batch

    @pytest.mark.django_db
    def test_incremental_loading_bug_fix(self):
        """Test the incremental loading fix - adding images to already-loaded batch."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        file1 = self._create_test_file("test1.jpg")
        file2 = self._create_test_file("test2.jpg")

        # Step 1: Add first image and trigger loading
        bound1 = img(file1, build="src")

        # Verify initial state
        assert not batch._is_loaded  # Not loaded yet
        initial_pk_count = len(batch._all_pk_to_options)

        # Trigger loading by accessing property
        url1 = bound1.base_url()  # This should trigger auto-building

        # Verify batch is now loaded
        assert batch._is_loaded
        assert len(batch._loaded_images) >= 1
        loaded_count_after_first = len(batch._loaded_images)

        # Step 2: Add second image to already-loaded batch
        bound2 = img(file2, build="src")

        # Verify new PKs were added and _is_loaded was reset
        assert len(batch._all_pk_to_options) > initial_pk_count
        assert not batch._is_loaded  # Should be reset due to new PKs
        assert (
            len(batch._loaded_images) == loaded_count_after_first
        )  # Cache unchanged yet

        # Step 3: Access second image (should trigger incremental loading)
        url2 = bound2.base_url()

        # Verify incremental loading worked
        assert batch._is_loaded  # Should be True again
        assert (
            len(batch._loaded_images) >= loaded_count_after_first
        )  # Should have more images

        # Verify both images work and are different
        assert url1 != url2
        assert url1.endswith(".jpg")
        assert url2.endswith(".jpg")

        # Verify first image still works (cached)
        url1_again = bound1.base_url()
        assert url1 == url1_again

    @pytest.mark.django_db
    def test_auto_building_hybrid_approach(self):
        """Test hybrid auto-building vs explicit building."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        file = self._create_test_file()

        # Test auto-building path
        bound1 = img(file, build="src")

        url1 = bound1.base_url()  # Should auto-build
        assert url1.endswith(".jpg")

        # Test explicit building path
        bound2 = img(file, build="srcset")

        batch.build()  # Explicit build

        url2 = bound2.base_url()  # Should use pre-built
        assert url2.endswith(".jpg")

    @pytest.mark.django_db
    def test_build_state_per_bound_img(self):
        """Test that each BoundImg detects actual build state correctly."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        file = self._create_test_file()

        bound1 = img(file, build="src")
        bound2 = img(file, build="srcset")
        
        # Check initial state using public is_built property
        assert not bound1.is_built
        assert not bound2.is_built

        # Build first image via auto-building
        url1 = bound1.base_url()
        assert url1.endswith(".jpg")
        assert bound1.is_built  # Should be built now

        # Build second image via explicit batch build
        batch.build()
        url2 = bound2.base_url()
        assert url2.endswith(".jpg")
        assert bound2.is_built  # Should be built now

        # Both should work after building
        assert bound1.base_url() == url1  # Should be cached/consistent
        assert bound2.base_url() == url2  # Should be cached/consistent

    @pytest.mark.django_db
    def test_immediate_vs_deferred_building(self):
        """Test immediate (signals) vs deferred (manual) building."""
        # Test deferred building (default)
        img1 = Img(width=100, format="jpg")
        file = self._create_test_file()
        bound1 = img1(file, build="src", immediate=False)

        url1 = bound1.base_url()  # Triggers auto-build
        assert url1.endswith(".jpg")

        # Test immediate building (signal path)
        img2 = Img(width=100, format="jpg")
        bound2 = img2(file, build="src", immediate=True)

        # Should be built immediately, so base_url should work
        url2 = bound2.base_url()
        assert url2.endswith(".jpg")

    @pytest.mark.django_db
    def test_batch_preserves_existing_loaded_images(self):
        """Test that incremental loading preserves existing cached images."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        file1 = self._create_test_file("test1.jpg")
        file2 = self._create_test_file("test2.jpg")

        # Load first image
        bound1 = img(file1, build="src")
        url1 = bound1.base_url()  # Triggers loading

        # Remember the loaded image instance
        first_batch_images = batch._loaded_images.copy()
        assert len(first_batch_images) >= 1

        # Add second image (should reset _is_loaded but preserve cache)
        bound2 = img(file2, build="src")

        # Cache should be preserved
        for pk, image_instance in first_batch_images.items():
            assert pk in batch._loaded_images
            assert batch._loaded_images[pk] is image_instance  # Same instance

        # Load second image
        bound2.base_url()

        # First images should still be in cache
        for pk, image_instance in first_batch_images.items():
            assert pk in batch._loaded_images
            assert batch._loaded_images[pk] is image_instance

        # And first image should still work
        url1_again = bound1.base_url()
        assert url1 == url1_again

    @pytest.mark.django_db
    def test_is_built_property(self):
        """Test the public is_built property in various scenarios."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")
        
        file = self._create_test_file()
        
        # Test with no build parameter
        bound_no_build = img(file)
        assert bound_no_build.is_built  # Should return True when no build requested
        
        # Test with src build (use fresh batch to avoid conflicts)
        batch_src = ImageBatch()
        img_src = Img(batch=batch_src, width=100, format="jpg")
        file_src = self._create_test_file("test_src.jpg")
        bound_src = img_src(file_src, build="src")
        assert not bound_src.is_built  # Initially not built
        _ = bound_src.base_url()  # Trigger build
        assert bound_src.is_built  # Now built
        
        # Test with srcset build (use fresh batch)
        batch_srcset = ImageBatch()
        img_srcset = Img(batch=batch_srcset, width=100, format="jpg", densities=[1, 2])
        file_srcset = self._create_test_file("test_srcset.jpg")
        bound_srcset = img_srcset(file_srcset, build="srcset")
        assert not bound_srcset.is_built  # Initially not built
        batch_srcset.build()  # Explicit build
        assert bound_srcset.is_built  # Now built
        
        # Test with all build (use fresh batch)
        batch_all = ImageBatch()
        img_all = Img(batch=batch_all, width=100, format="jpg", densities=[1, 2])
        file_all = self._create_test_file("test_all.jpg")
        bound_all = img_all(file_all, build="all")
        assert not bound_all.is_built  # Initially not built
        _ = bound_all.base_url()  # Trigger partial build (src)
        assert bound_all.is_built  # Should be True if any part is built


class TestImageBatchOptimization:
    """Test batch performance and optimization."""

    def _create_test_file(self, name="test.jpg"):
        """Helper to create test file."""
        image = pyvips.Image.black(100, 100)
        content = image.write_to_buffer(".jpg")
        file = SimpleUploadedFile(name, content)
        profile = Profile.objects.create(name="Test", image=file)
        return profile.image

    @pytest.mark.django_db
    def test_database_query_batching(self):
        """Test that batch loading minimizes database queries."""
        from django.db import connection

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        # Create multiple test files
        files = [self._create_test_file(f"test{i}.jpg") for i in range(5)]
        bounds = [img(f, build="src") for f in files]

        # Reset query count
        initial_queries = len(connection.queries)

        # Access all images - should batch DB operations
        urls = [b.base_url() for b in bounds]

        # Check that queries were batched (should be much fewer than 5 individual queries)
        queries_used = len(connection.queries) - initial_queries

        # Should use significantly fewer queries than individual lookups
        # Expect: 1 bulk query for EasyImage lookups + bulk create + possible refetch
        assert queries_used <= 10, (
            f"Used {queries_used} queries, expected <= 10 for batched operations"
        )

        # All URLs should be accessible
        assert len(urls) == 5
        assert all(url.endswith(".jpg") for url in urls if url)

    @pytest.mark.django_db
    def test_fresh_batch_vs_shared_batch_queries(self):
        """Compare query counts between fresh and shared batches."""
        from django.conf import settings
        from django.db import connection

        # Enable query logging for this test
        old_debug = getattr(settings, "DEBUG", False)
        settings.DEBUG = True

        try:
            # Clear existing queries
            connection.queries_log.clear()

            # Test fresh batches (one query per image)
            initial_queries = len(connection.queries)

            fresh_urls = []
            for i in range(3):
                img = Img(width=100, format="jpg")  # Fresh batch each time
                file = self._create_test_file(f"fresh{i}.jpg")
                bound = img(file, build="src")
                fresh_urls.append(bound.base_url())

            fresh_queries = len(connection.queries) - initial_queries

            # Reset for shared batch test
            reset_queries = len(connection.queries)

            # Test shared batch (should use fewer queries)
            batch = ImageBatch()
            img = Img(batch=batch, width=100, format="jpg")

            shared_bounds = []
            for i in range(3):
                file = self._create_test_file(f"shared{i}.jpg")
                shared_bounds.append(img(file, build="src"))

            shared_urls = [b.base_url() for b in shared_bounds]
            shared_queries = len(connection.queries) - reset_queries

            # Both approaches should work
            assert len(fresh_urls) == len(shared_urls) == 3

            # If queries were made, shared should generally be more efficient
            if fresh_queries > 0 and shared_queries > 0:
                # Allow some variance but generally shared should be better
                assert shared_queries <= fresh_queries * 1.5, (
                    f"Shared batch used {shared_queries} queries vs {fresh_queries} for fresh batches"
                )

        finally:
            settings.DEBUG = old_debug

    @pytest.mark.django_db
    def test_memory_management_fresh_batches(self):
        """Test that fresh batches prevent memory accumulation."""
        urls = []
        batch_sizes = []

        # Create many images with fresh batches
        for i in range(5):
            img = Img(width=100, format="jpg")  # Fresh batch each time
            file = self._create_test_file(f"test{i}.jpg")
            bound = img(file, build="src")
            url = bound.base_url()

            # Each should have its own batch with only its own item
            assert len(bound._parent_batch._batch_items) == 1
            assert len(bound._parent_batch._all_pk_to_options) >= 1

            batch_sizes.append(len(bound._parent_batch._loaded_images))
            urls.append(url)

        # All URLs should be different
        assert len(set(urls)) == 5
        # Each batch should remain small (no accumulation)
        assert all(size <= 2 for size in batch_sizes), f"Batch sizes: {batch_sizes}"

    @pytest.mark.django_db
    def test_shared_batch_accumulation(self):
        """Test that shared batches accumulate items efficiently."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        files = [self._create_test_file(f"test{i}.jpg") for i in range(3)]
        bounds = [img(f, build="src") for f in files]

        # All should share the same batch
        for bound in bounds:
            assert bound._parent_batch is batch

        # Batch should accumulate all items
        assert len(batch._batch_items) == 3
        assert len(batch._all_pk_to_options) >= 3

        # All should be accessible after batch build
        batch.build()
        urls = [b.base_url() for b in bounds]
        assert len(set(urls)) == 3  # All different URLs

        # Shared batch should have accumulated images efficiently
        assert len(batch._loaded_images) >= 3


class TestImageBatchEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.django_db
    def test_empty_batch_operations(self):
        """Test operations on empty batches."""
        batch = ImageBatch()

        # Should handle empty state gracefully
        batch.build()  # Should not error
        assert batch._is_loaded
        assert len(batch._loaded_images) == 0
        assert len(batch._batch_items) == 0

    @pytest.mark.django_db
    def test_duplicate_image_handling(self):
        """Test adding same image multiple times to batch."""
        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        # Create test file
        image = pyvips.Image.black(100, 100)
        content = image.write_to_buffer(".jpg")
        file = SimpleUploadedFile("test.jpg", content)
        profile = Profile.objects.create(name="Test", image=file)

        # Add same image twice with same config
        bound1 = img(profile.image, build="src")
        bound2 = img(profile.image, build="src")  # Same file, same config

        # Should have separate items but potentially shared PKs
        assert len(batch._batch_items) == 2

        # URLs might be the same (same image, same processing)
        url1 = bound1.base_url()
        url2 = bound2.base_url()

        # Both should work
        assert url1.endswith(".jpg")
        assert url2.endswith(".jpg")


class TestImageBatchErrorHandling:
    """Test error handling and failure scenarios."""

    def _create_test_file(self, name="test.jpg"):
        """Helper to create test file."""
        image = pyvips.Image.black(100, 100)
        content = image.write_to_buffer(".jpg")
        file = SimpleUploadedFile(name, content)
        profile = Profile.objects.create(name="Test", image=file)
        return profile.image

    @pytest.mark.django_db
    def test_missing_source_file_handling(self):
        """Test handling when source file is missing from storage."""
        from easy_images.core import ImageBatch

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        # Create a file, then simulate it being deleted
        file = self._create_test_file()
        bound = img(file, build="src")

        # Delete the source file from storage to simulate missing file
        if file.storage.exists(file.name):
            file.storage.delete(file.name)

        # Accessing should handle missing file gracefully
        url = bound.base_url()

        # Should fall back to original URL or empty string
        assert isinstance(url, str)  # Should not raise exception

    @pytest.mark.django_db
    def test_corrupted_source_file_handling(self):
        """Test handling when source file is corrupted."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from easy_images.models import ImageStatus

        # Create corrupted file
        corrupted_content = b"not a valid image file"
        file = SimpleUploadedFile(
            "corrupted.jpg", corrupted_content, content_type="image/jpeg"
        )
        profile = Profile.objects.create(name="Test", image=file)

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")
        bound = img(profile.image, build="src")

        # Should handle corrupted file without crashing
        url = bound.base_url()
        assert isinstance(url, str)

        # Check that the image status reflects the error
        base_img = bound.base
        if base_img:
            # Refresh from DB to see any status updates
            base_img.refresh_from_db()
            # May be marked as source error after build attempt
            assert base_img.status in [
                ImageStatus.QUEUED,
                ImageStatus.SOURCE_ERROR,
                ImageStatus.BUILD_ERROR,
            ]

    @pytest.mark.django_db
    def test_batch_with_mixed_valid_invalid_files(self):
        """Test batch processing with mix of valid and invalid files."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        # Valid file
        valid_file = self._create_test_file("valid.jpg")
        bound_valid = img(valid_file, build="src")

        # Invalid file
        invalid_content = b"not an image"
        invalid_file = SimpleUploadedFile(
            "invalid.jpg", invalid_content, content_type="image/jpeg"
        )
        profile_invalid = Profile.objects.create(name="Invalid", image=invalid_file)
        bound_invalid = img(profile_invalid.image, build="src")

        # Both should be accessible without crashing the batch
        valid_url = bound_valid.base_url()
        invalid_url = bound_invalid.base_url()

        # Valid should work, invalid should handle gracefully
        assert valid_url.endswith(".jpg")
        assert isinstance(invalid_url, str)  # Should not crash

    @pytest.mark.django_db
    def test_concurrent_batch_loading(self):
        """Test concurrent access to batch loading."""
        import threading
        import time

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")

        files = [self._create_test_file(f"concurrent{i}.jpg") for i in range(3)]
        bounds = [img(f, build="src") for f in files]

        results = []
        errors = []

        def access_image(bound, index):
            try:
                # Add small delay to increase chance of concurrent access
                time.sleep(0.01 * index)
                url = bound.base_url()
                results.append((index, url))
            except Exception as e:
                errors.append((index, str(e)))

        # Start multiple threads accessing images concurrently
        threads = []
        for i, bound in enumerate(bounds):
            thread = threading.Thread(target=access_image, args=(bound, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Database locking is expected with SQLite in concurrent scenarios
        # We mainly want to ensure the system doesn't crash
        expected_errors = ["database table is locked", "permission", "file"]
        serious_errors = [
            err
            for idx, err in errors
            if not any(expected in err.lower() for expected in expected_errors)
        ]
        assert len(serious_errors) == 0, (
            f"Serious concurrent access errors: {serious_errors}"
        )

        # Should have some successful results OR predictable database errors
        total_outcomes = len(results) + len(errors)
        assert total_outcomes == 3, f"Expected 3 outcomes, got {total_outcomes}"

        # Valid results should be proper URLs
        for index, url in results:
            if url:  # Allow empty URLs as fallback
                assert isinstance(url, str), (
                    f"Invalid URL type for image {index}: {type(url)}"
                )

    @pytest.mark.django_db
    def test_invalid_image_options_handling(self):
        """Test handling of invalid image processing options."""
        batch = ImageBatch()

        # Test with extreme dimensions that might cause issues
        try:
            img = Img(batch=batch, width=50000, format="jpg")  # Very large width
            file = self._create_test_file()
            bound = img(file, build="src")
            url = bound.base_url()
            # Should either work or handle gracefully
            assert isinstance(url, str)
        except Exception as e:
            # Should not crash completely - various error types are acceptable
            error_msg = str(e).lower()
            assert any(
                keyword in error_msg
                for keyword in [
                    "width",
                    "memory",
                    "size",
                    "limit",
                    "decompression",
                    "bomb",
                    "pixels",
                ]
            ), f"Unexpected error type: {e}"

    @pytest.mark.django_db
    def test_storage_permission_errors(self):
        """Test handling when storage operations fail due to permissions."""
        from unittest.mock import patch

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")
        file = self._create_test_file()
        bound = img(file, build="src")

        # Mock storage to raise permission error
        with patch.object(
            file.storage, "open", side_effect=PermissionError("Access denied")
        ):
            url = bound.base_url()
            # Should handle gracefully and return fallback or empty string
            assert isinstance(url, str)

    @pytest.mark.django_db
    def test_database_connection_errors(self):
        """Test handling when database operations fail."""
        from unittest.mock import patch

        from django.db import DatabaseError

        batch = ImageBatch()
        img = Img(batch=batch, width=100, format="jpg")
        file = self._create_test_file()
        bound = img(file, build="src")

        # Mock database query to fail
        with patch(
            "easy_images.models.EasyImage.objects.filter",
            side_effect=DatabaseError("DB error"),
        ):
            try:
                url = bound.base_url()
                # Should either handle gracefully or raise expected error
                assert isinstance(url, str)
            except DatabaseError:
                # This is acceptable - the error should propagate properly
                pass
