import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from salesforce.crawl import TrailheadCrawler
from salesforce.auth import LoginResult, SalesforceAuth
from salesforce.parse import ContentItem, LessonContent, ModuleContent


class TestTrailheadCrawlerIntegration(unittest.TestCase):
    """Integration tests for TrailheadCrawler with mocked SalesforceAuth."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.crawler = TrailheadCrawler(output_dir=self.temp_dir)

        # Mock SalesforceAuth
        self.mock_auth = Mock(spec=SalesforceAuth)
        self.mock_page = Mock()
        self.mock_auth.get_page.return_value = self.mock_page

        # Set up fixtures directory
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures"

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_mock_page_for_module(self):
        """Set up mock page for module parsing."""
        # Mock module content
        mock_module = ModuleContent(
            title="Test Module",
            url="https://trailhead.salesforce.com/content/learn/modules/test_module",
            description="Test module description",
            lessons=[
                {
                    "title": "Lesson 1",
                    "url": "https://trailhead.salesforce.com/content/learn/modules/test_module/lesson1",
                },
                {
                    "title": "Lesson 2",
                    "url": "https://trailhead.salesforce.com/content/learn/modules/test_module/lesson2",
                },
            ],
            estimated_time="1 hour",
            difficulty="Beginner",
            prerequisites=["Basic knowledge"],
        )

        # Mock lesson content
        mock_lesson = LessonContent(
            title="Test Lesson",
            url="https://trailhead.salesforce.com/content/learn/modules/test_module/lesson1",
            content=[
                ContentItem(text="Test heading", element_type="heading", level=1),
                ContentItem(text="Test paragraph", element_type="text"),
            ],
            learning_objectives=["Learn something", "Understand concepts"],
            instructions=["Step 1", "Step 2"],
            links=[{"text": "Test Link", "url": "https://example.com"}],
            estimated_time="30 min",
        )

        return mock_module, mock_lesson

    @patch("salesforce.crawl.parse_module")
    @patch("salesforce.crawl.parse_lesson")
    def test_crawl_module_success(self, mock_parse_lesson, mock_parse_module):
        """Test successful module crawling."""
        # Set up mocks
        mock_module, mock_lesson = self._setup_mock_page_for_module()
        mock_parse_module.return_value = mock_module
        mock_parse_lesson.return_value = mock_lesson

        # Mock page navigation
        self.mock_page.url = (
            "https://trailhead.salesforce.com/content/learn/modules/test_module"
        )

        # Test crawling
        module_url = (
            "https://trailhead.salesforce.com/content/learn/modules/test_module"
        )
        result = self.crawler.crawl_module(module_url, self.mock_auth)

        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIn("module", result)
        self.assertIn("lessons", result)
        self.assertIn("crawl_timestamp", result)
        self.assertIn("total_lessons", result)
        self.assertIn("successful_lessons", result)
        self.assertIn("failed_lessons", result)

        # Verify module data
        self.assertEqual(result["module"]["title"], "Test Module")
        self.assertEqual(result["module"]["description"], "Test module description")
        self.assertEqual(len(result["module"]["lessons"]), 2)

        # Verify lesson data
        self.assertEqual(len(result["lessons"]), 2)
        self.assertEqual(result["lessons"][0]["title"], "Test Lesson")

        # Verify file was saved
        module_files = list(Path(self.temp_dir).glob("modules/*.json"))
        self.assertEqual(len(module_files), 1)

        # Verify file content
        with open(module_files[0], "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["module"]["title"], "Test Module")

        # Verify progress was saved
        progress_file = Path(self.temp_dir) / "progress.json"
        self.assertTrue(progress_file.exists())

        with open(progress_file, "r") as f:
            progress = json.load(f)
        self.assertIn(module_url, progress["visited_urls"])

    @patch("salesforce.crawl.parse_module")
    def test_crawl_module_failure(self, mock_parse_module):
        """Test module crawling failure handling."""
        # Make parsing fail
        mock_parse_module.side_effect = Exception("Parsing failed")

        # Test crawling
        module_url = (
            "https://trailhead.salesforce.com/content/learn/modules/test_module"
        )
        result = self.crawler.crawl_module(module_url, self.mock_auth)

        # Verify failure handling
        self.assertIsNone(result)
        # Note: We no longer track failed URLs since we removed cache functionality

    def test_crawl_module_already_visited(self):
        """Test that modules are always crawled (no cache)."""
        # This test is no longer relevant since we removed cache functionality
        # Modules are always crawled fresh now
        module_url = (
            "https://trailhead.salesforce.com/content/learn/modules/test_module"
        )

        # Mock module content
        mock_module, mock_lesson = self._setup_mock_page_for_module()

        with (
            patch("salesforce.crawl.parse_module", return_value=mock_module),
            patch("salesforce.crawl.parse_lesson", return_value=mock_lesson),
        ):
            result = self.crawler.crawl_module(module_url, self.mock_auth)

        # Verify module was crawled (not skipped)
        self.assertIsNotNone(result)
        self.assertIn("module", result)

    def test_crawl_trail_success(self):
        """Test successful trail crawling."""
        # Mock trail info extraction
        mock_trail_info = {
            "title": "Test Trail",
            "description": "Test trail description",
            "url": "https://trailhead.salesforce.com/trails/test_trail",
            "modules": [
                {
                    "title": "Module 1",
                    "url": "https://trailhead.salesforce.com/content/learn/modules/module1",
                },
                {
                    "title": "Module 2",
                    "url": "https://trailhead.salesforce.com/content/learn/modules/module2",
                },
            ],
        }

        # Mock module crawling results
        mock_module_result = {"module": {"title": "Module 1"}, "lessons": []}

        with (
            patch.object(
                self.crawler, "_extract_trail_info", return_value=mock_trail_info
            ),
            patch.object(self.crawler, "crawl_module", return_value=mock_module_result),
        ):
            trail_url = "https://trailhead.salesforce.com/trails/test_trail"
            result = self.crawler.crawl_trail(trail_url, self.mock_auth)

        # Verify result structure
        self.assertIn("trail", result)
        self.assertIn("modules", result)
        self.assertIn("crawl_timestamp", result)
        self.assertIn("crawl_date", result)

        # Verify trail data
        self.assertEqual(result["trail"]["title"], "Test Trail")
        self.assertEqual(len(result["trail"]["modules"]), 2)

        # Verify modules data
        self.assertEqual(len(result["modules"]), 2)

        # Verify file was saved
        trail_files = list(Path(self.temp_dir).glob("trails/*.json"))
        self.assertEqual(len(trail_files), 1)

    def test_crawl_trail_failure(self):
        """Test trail crawling failure handling."""
        # Mock trail info extraction to fail
        with patch.object(
            self.crawler,
            "_extract_trail_info",
            side_effect=Exception("Trail parsing failed"),
        ):
            trail_url = "https://trailhead.salesforce.com/trails/test_trail"
            result = self.crawler.crawl_trail(trail_url, self.mock_auth)

        # Verify error handling
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Trail parsing failed")

    def test_crawl_urls_from_file_success(self):
        """Test crawling URLs from file."""
        # Create test URLs file
        urls_file = Path(self.temp_dir) / "test_urls.txt"
        with open(urls_file, "w") as f:
            f.write("https://trailhead.salesforce.com/content/learn/modules/module1\n")
            f.write("https://trailhead.salesforce.com/trails/trail1\n")
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            f.write("https://trailhead.salesforce.com/content/learn/modules/module2\n")

        # Mock crawling methods
        mock_module_result = {"module": {"title": "Test Module"}}
        mock_trail_result = {"trail": {"title": "Test Trail"}}

        with (
            patch.object(self.crawler, "crawl_module", return_value=mock_module_result),
            patch.object(self.crawler, "crawl_trail", return_value=mock_trail_result),
        ):
            result = self.crawler.crawl_urls_from_file(str(urls_file), self.mock_auth)

        # Verify results
        self.assertEqual(len(result), 3)  # 2 modules + 1 trail
        self.assertIn(
            "https://trailhead.salesforce.com/content/learn/modules/module1", result
        )
        self.assertIn("https://trailhead.salesforce.com/trails/trail1", result)
        self.assertIn(
            "https://trailhead.salesforce.com/content/learn/modules/module2", result
        )

        # Verify batch results file was saved
        batch_files = list(Path(self.temp_dir).glob("batch_results_*.json"))
        self.assertEqual(len(batch_files), 1)

    def test_crawl_urls_from_file_not_found(self):
        """Test crawling URLs from non-existent file."""
        non_existent_file = Path(self.temp_dir) / "nonexistent.txt"
        result = self.crawler.crawl_urls_from_file(
            str(non_existent_file), self.mock_auth
        )

        # Verify error handling
        self.assertIn("error", result)

    def test_navigate_with_retry_success(self):
        """Test successful navigation with retry logic."""
        test_url = "https://example.com"

        # Mock successful navigation
        self.mock_page.goto.return_value = None
        self.mock_page.wait_for_load_state.return_value = None

        # Should not raise exception
        self.crawler._navigate_with_retry(self.mock_page, test_url)

        # Verify page.goto was called with correct parameters
        self.mock_page.goto.assert_called_once_with(
            test_url, wait_until="networkidle", timeout=30000
        )

    def test_navigate_with_retry_failure(self):
        """Test navigation failure and retry logic."""
        test_url = "https://example.com"

        # Mock navigation failures
        self.mock_page.goto.side_effect = Exception("Navigation failed")

        # Should raise exception after retries
        with self.assertRaises(Exception):
            self.crawler._navigate_with_retry(self.mock_page, test_url, max_retries=2)

        # Verify multiple attempts were made
        self.assertEqual(self.mock_page.goto.call_count, 2)

    def test_extract_trail_info(self):
        """Test trail information extraction."""
        # Mock page elements
        mock_title_element = Mock()
        mock_title_element.is_visible.return_value = True
        mock_title_element.text_content.return_value = "Test Trail Title"

        mock_desc_element = Mock()
        mock_desc_element.is_visible.return_value = True
        mock_desc_element.text_content.return_value = (
            "Test trail description for testing"
        )

        mock_module_element = Mock()
        mock_module_element.get_attribute.return_value = (
            "/content/learn/modules/test_module"
        )
        mock_module_element.text_content.return_value = "Test Module"

        # Mock locator calls
        self.mock_page.locator.side_effect = self._mock_locator_for_trail_extraction(
            mock_title_element, mock_desc_element, mock_module_element
        )
        self.mock_page.url = "https://trailhead.salesforce.com/trails/test_trail"

        # Test extraction
        trail_info = self.crawler._extract_trail_info(self.mock_page)

        # Verify results
        self.assertEqual(trail_info["title"], "Test Trail Title")
        self.assertEqual(
            trail_info["description"], "Test trail description for testing"
        )
        self.assertEqual(
            trail_info["url"], "https://trailhead.salesforce.com/trails/test_trail"
        )
        # Note: The _extract_trail_info method doesn't extract modules, only basic trail info

    def _mock_locator_for_trail_extraction(self, title_elem, desc_elem, module_elem):
        """Helper to mock locator calls for trail extraction."""

        def locator_side_effect(selector):
            mock_locator = Mock()

            if selector == "h1":
                mock_locator.first = title_elem
            elif selector in [
                "[data-testid='trail-description']",
                ".trail-description",
                ".description",
                "p:first-of-type",
            ]:
                mock_locator.first = desc_elem
            elif selector in [
                ".trail-modules a",
                ".modules-list a",
                ".module-list a",
                "[data-testid='module-link']",
            ]:
                mock_locator.all.return_value = [module_elem]
            else:
                mock_locator.first = Mock()
                mock_locator.first.is_visible.return_value = False
                mock_locator.all.return_value = []

            return mock_locator

        return locator_side_effect

    def test_save_and_load_progress(self):
        """Test that progress tracking is disabled (no cache)."""
        # This test is no longer relevant since we removed progress tracking
        # Progress is no longer saved or loaded
        self.assertEqual(len(self.crawler.visited_urls), 0)
        self.assertEqual(len(self.crawler.failed_urls), 0)

    def test_load_existing_module_data(self):
        """Test that existing data loading is disabled (no cache)."""
        # This test is no longer relevant since we removed cache functionality
        result = self.crawler._load_existing_data("https://example.com/test")
        self.assertIsNone(result)

    def test_load_existing_lesson_data(self):
        """Test that existing lesson data loading is disabled (no cache)."""
        # This test is no longer relevant since we removed cache functionality
        result = self.crawler._load_existing_lesson_data("https://example.com/test")
        self.assertIsNone(result)

    def test_get_stats(self):
        """Test statistics generation."""
        # Add some data to crawler
        self.crawler.visited_urls.update(["url1", "url2", "url3"])
        self.crawler.failed_urls.update(["url4"])

        # Get stats
        stats = self.crawler.get_stats()

        # Verify stats
        self.assertEqual(stats["visited_urls"], 3)
        self.assertEqual(stats["failed_urls"], 1)
        self.assertEqual(stats["success_rate"], 75.0)  # 3/(3+1) * 100
        self.assertEqual(stats["output_directory"], self.temp_dir)

    def test_get_stats_no_data(self):
        """Test statistics when no data exists."""
        stats = self.crawler.get_stats()

        # Verify stats
        self.assertEqual(stats["visited_urls"], 0)
        self.assertEqual(stats["failed_urls"], 0)
        self.assertEqual(stats["success_rate"], 0)


class TestCrawlerFileOperations(unittest.TestCase):
    """Test file operations of TrailheadCrawler."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.crawler = TrailheadCrawler(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_module_data(self):
        """Test saving module data to file."""
        test_data = {
            "module": {"title": "Test Module"},
            "lessons": [],
            "crawl_timestamp": 1234567890,
        }

        module_url = (
            "https://trailhead.salesforce.com/content/learn/modules/test-module"
        )
        self.crawler._save_module_data(module_url, test_data)

        # Verify file was created with hash-based naming
        expected_file = Path(self.temp_dir) / f"module_{hash(module_url)}.json"
        self.assertTrue(expected_file.exists())

    def test_save_trail_data(self):
        """Test saving trail data to file."""
        test_data = {
            "trail": {"title": "Test Trail"},
            "modules": [],
            "crawl_timestamp": 1234567890,
        }

        trail_url = "https://trailhead.salesforce.com/trails/test-trail"
        self.crawler._save_trail_data(trail_url, test_data)

        # Verify file was created with hash-based naming
        expected_file = Path(self.temp_dir) / f"trail_{hash(trail_url)}.json"
        self.assertTrue(expected_file.exists())

    def test_save_batch_results(self):
        """Test saving batch results."""
        test_results = {
            "url1": {"module": {"title": "Module 1"}},
            "url2": {"module": {"title": "Module 2"}},
        }

        self.crawler._save_batch_results(test_results)

        # Verify batch file was created
        batch_files = list(Path(self.temp_dir).glob("batch_results_*.json"))
        self.assertEqual(len(batch_files), 1)

        # Verify file content
        with open(batch_files[0], "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, test_results)

    def test_directory_creation(self):
        """Test that necessary directories are created."""
        # Test module directory creation
        test_data = {"module": {"title": "Test"}}
        self.crawler._save_module_data("https://example.com/test", test_data)

        # Verify the main output directory exists
        self.assertTrue(Path(self.temp_dir).exists())


if __name__ == "__main__":
    unittest.main()
