"""Test helper utilities for TrailBuster tests."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

from playwright.sync_api import sync_playwright

from salesforce.auth import LoginResult, SalesforceAuth
from tests.fixtures.test_data import (
    MINIMAL_LESSON_HTML,
    MINIMAL_MODULE_HTML,
    MINIMAL_TRAIL_HTML,
    create_test_html_file,
)


class TestEnvironmentHelper:
    """Helper class to manage test environment setup and teardown.

    Note: This is not a test class, just a helper utility.
    """

    __test__ = False  # Tell pytest not to collect this class

    def __init__(self):
        self.temp_dir = None
        self.playwright = None
        self.browser = None
        self.context = None

    def setup(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        return self

    def teardown(self):
        """Clean up test environment."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self):
        return self.setup()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown()

    def create_page(self):
        """Create a new page for testing."""
        return self.context.new_page()

    def create_html_fixture(self, html_content: str, filename: str) -> str:
        """Create an HTML fixture file."""
        return create_test_html_file(html_content, filename, self.temp_dir)

    def create_urls_file(self, urls: list) -> str:
        """Create a URLs file for testing."""
        urls_file = Path(self.temp_dir) / "test_urls.txt"
        with open(urls_file, "w") as f:
            for url in urls:
                f.write(f"{url}\n")
        return str(urls_file)


class MockSalesforceAuth:
    """Mock SalesforceAuth for testing."""

    def __init__(self, test_env: TestEnvironmentHelper):
        self.test_env = test_env
        self.page = None
        self.login_result = LoginResult(
            is_logged_in=True, session_restored=False, error=None
        )

    def get_page(self):
        """Get a mock page."""
        if not self.page:
            self.page = self.test_env.create_page()
        return self.page

    def login(self, email: str, use_saved_session: bool = True) -> LoginResult:
        """Mock login method."""
        return self.login_result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            self.page.close()


class MockPageHelper:
    """Helper class to create mock Playwright page objects."""

    @staticmethod
    def create_mock_page_with_html(html_content: str):
        """Create a mock page with specific HTML content."""
        mock_page = Mock()
        mock_page.url = "https://test.example.com"
        mock_page.title.return_value = "Test Page"

        # Mock the set_content method
        mock_page.set_content = Mock()

        # Mock locator calls based on HTML content
        MockPageHelper._setup_locator_mocks(mock_page, html_content)

        return mock_page

    @staticmethod
    def _setup_locator_mocks(mock_page, html_content: str):
        """Set up locator mocks based on HTML content."""

        # This is a simplified version - in a real implementation,
        # you'd parse the HTML and set up appropriate mocks
        def locator_side_effect(selector):
            mock_locator = Mock()
            mock_locator.first = Mock()
            mock_locator.all.return_value = []
            mock_locator.first.is_visible.return_value = True
            mock_locator.first.text_content.return_value = "Mock Content"
            return mock_locator

        mock_page.locator.side_effect = locator_side_effect


def create_test_progress_file(
    temp_dir: str, visited_urls: list = None, failed_urls: list = None
) -> str:
    """Create a test progress file."""
    progress = {
        "visited_urls": visited_urls or [],
        "failed_urls": failed_urls or [],
        "last_updated": 1234567890,
    }

    progress_file = Path(temp_dir) / "progress.json"
    with open(progress_file, "w") as f:
        json.dump(progress, f)

    return str(progress_file)


def create_test_module_data_file(
    temp_dir: str, module_url: str, module_data: dict
) -> str:
    """Create a test module data file."""
    from urllib.parse import urlparse

    modules_dir = Path(temp_dir) / "modules"
    modules_dir.mkdir(exist_ok=True)

    parsed_url = urlparse(module_url)
    filename = parsed_url.path.replace("/", "_").replace("-", "_") + ".json"
    file_path = modules_dir / filename

    with open(file_path, "w") as f:
        json.dump(module_data, f, indent=2)

    return str(file_path)


def create_test_trail_data_file(temp_dir: str, trail_url: str, trail_data: dict) -> str:
    """Create a test trail data file."""
    from urllib.parse import urlparse

    trails_dir = Path(temp_dir) / "trails"
    trails_dir.mkdir(exist_ok=True)

    parsed_url = urlparse(trail_url)
    filename = parsed_url.path.replace("/", "_").replace("-", "_") + ".json"
    file_path = trails_dir / filename

    with open(file_path, "w") as f:
        json.dump(trail_data, f, indent=2)

    return str(file_path)


def assert_content_item_valid(content_item, test_case):
    """Assert that a ContentItem is valid."""
    test_case.assertIsNotNone(content_item.text)
    test_case.assertIsInstance(content_item.text, str)
    test_case.assertGreater(len(content_item.text.strip()), 0)
    test_case.assertIn(
        content_item.element_type, ["text", "link", "code", "list", "heading"]
    )

    if content_item.element_type == "heading":
        test_case.assertIsNotNone(content_item.level)
        test_case.assertIsInstance(content_item.level, int)
        test_case.assertGreaterEqual(content_item.level, 1)
        test_case.assertLessEqual(content_item.level, 6)

    if content_item.element_type == "link":
        test_case.assertIsNotNone(content_item.url)
        test_case.assertIsInstance(content_item.url, str)


def assert_lesson_content_valid(lesson_content, test_case):
    """Assert that a LessonContent object is valid."""
    test_case.assertIsNotNone(lesson_content.title)
    test_case.assertIsInstance(lesson_content.title, str)
    test_case.assertGreater(len(lesson_content.title.strip()), 0)

    test_case.assertIsNotNone(lesson_content.url)
    test_case.assertIsInstance(lesson_content.url, str)

    test_case.assertIsInstance(lesson_content.content, list)
    test_case.assertIsInstance(lesson_content.learning_objectives, list)
    test_case.assertIsInstance(lesson_content.instructions, list)
    test_case.assertIsInstance(lesson_content.links, list)

    # Validate content items
    for item in lesson_content.content:
        assert_content_item_valid(item, test_case)

    # Validate links
    for link in lesson_content.links:
        test_case.assertIn("text", link)
        test_case.assertIn("url", link)
        test_case.assertIsInstance(link["text"], str)
        test_case.assertIsInstance(link["url"], str)


def assert_module_content_valid(module_content, test_case):
    """Assert that a ModuleContent object is valid."""
    test_case.assertIsNotNone(module_content.title)
    test_case.assertIsInstance(module_content.title, str)
    test_case.assertGreater(len(module_content.title.strip()), 0)

    test_case.assertIsNotNone(module_content.url)
    test_case.assertIsInstance(module_content.url, str)

    test_case.assertIsNotNone(module_content.description)
    test_case.assertIsInstance(module_content.description, str)

    test_case.assertIsInstance(module_content.lessons, list)

    # Validate lessons
    for lesson in module_content.lessons:
        test_case.assertIn("title", lesson)
        test_case.assertIn("url", lesson)
        test_case.assertIsInstance(lesson["title"], str)
        test_case.assertIsInstance(lesson["url"], str)

    # Validate optional fields
    if module_content.prerequisites:
        test_case.assertIsInstance(module_content.prerequisites, list)
        for prereq in module_content.prerequisites:
            test_case.assertIsInstance(prereq, str)


def create_comprehensive_test_suite():
    """Create a comprehensive test suite for all modules."""
    import unittest

    from tests.integration.test_crawl import (
        TestCrawlerFileOperations,
        TestTrailheadCrawlerIntegration,
    )

    # Import all test modules
    from tests.unit.test_parse import TestParseModule, TestParseWithRealFixtures

    # Create test suite
    suite = unittest.TestSuite()

    # Add unit tests
    suite.addTest(unittest.makeSuite(TestParseModule))
    suite.addTest(unittest.makeSuite(TestParseWithRealFixtures))

    # Add integration tests
    suite.addTest(unittest.makeSuite(TestTrailheadCrawlerIntegration))
    suite.addTest(unittest.makeSuite(TestCrawlerFileOperations))

    return suite


def run_all_tests():
    """Run all tests with detailed output."""
    import unittest

    suite = create_comprehensive_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result
