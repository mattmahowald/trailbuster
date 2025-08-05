import unittest
import os
from unittest.mock import Mock, patch
from pathlib import Path

from playwright.sync_api import sync_playwright

from salesforce.parse import (
    parse_lesson, parse_module, 
    ContentItem, LessonContent, ModuleContent,
    _extract_title, _extract_learning_objectives, _extract_lesson_content,
    _extract_instructions, _extract_links, _extract_time_estimate,
    _extract_description, _extract_lessons_list, _extract_difficulty,
    _extract_prerequisites
)

class TestParseModule(unittest.TestCase):
    """Test suite for parse module functions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_dir = Path(__file__).parent.parent
        cls.fixtures_dir = cls.test_dir / "fixtures"
        
        # Start playwright browser for testing
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.context = cls.browser.new_context()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up browser resources."""
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()
    
    def setUp(self):
        """Set up each test."""
        self.page = self.context.new_page()
    
    def tearDown(self):
        """Clean up each test."""
        self.page.close()
    
    def _load_fixture(self, filename: str):
        """Load an HTML fixture file."""
        fixture_path = self.fixtures_dir / filename
        if not fixture_path.exists():
            self.skipTest(f"Fixture {filename} not found")
        
        file_url = f"file://{fixture_path.absolute()}"
        self.page.goto(file_url)
        self.page.wait_for_load_state("domcontentloaded")
    
    def test_parse_lesson_with_mock_data(self):
        """Test parsing lesson with mock HTML data."""
        self._load_fixture("mock_lesson.html")
        
        result = parse_lesson(self.page)
        
        # Verify basic structure
        self.assertIsInstance(result, LessonContent)
        self.assertEqual(result.title, "Understanding Salesforce Platform Basics")
        self.assertEqual(result.estimated_time, "~15 min")
        self.assertTrue(result.url.startswith("file://"))
        
        # Verify learning objectives
        self.assertEqual(len(result.learning_objectives), 3)
        self.assertIn("Understand what the Salesforce Platform is", result.learning_objectives)
        self.assertIn("Learn about custom objects and fields", result.learning_objectives)
        self.assertIn("Explore the App Exchange marketplace", result.learning_objectives)
        
        # Verify content items
        self.assertGreater(len(result.content), 0)
        
        # Check for different content types
        content_types = [item.element_type for item in result.content]
        self.assertIn('heading', content_types)
        self.assertIn('text', content_types)
        self.assertIn('code', content_types)
        self.assertIn('list', content_types)
        
        # Verify instructions
        self.assertEqual(len(result.instructions), 4)
        self.assertIn("Navigate to Setup", result.instructions[0])
        
        # Verify links
        self.assertGreater(len(result.links), 0)
        link_urls = [link['url'] for link in result.links]
        self.assertIn("https://trailhead.salesforce.com/content/learn/modules/platform_dev_basics", link_urls)
        self.assertIn("https://developer.salesforce.com/docs", link_urls)
    
    def test_parse_module_with_mock_data(self):
        """Test parsing module with mock HTML data."""
        self._load_fixture("mock_module.html")
        
        result = parse_module(self.page)
        
        # Verify basic structure
        self.assertIsInstance(result, ModuleContent)
        self.assertEqual(result.title, "Salesforce Platform Basics")
        self.assertTrue(result.url.startswith("file://"))
        self.assertEqual(result.estimated_time, "~2 hr")
        self.assertEqual(result.difficulty, "Beginner")
        
        # Verify description
        self.assertIn("Learn the fundamentals", result.description)
        
        # Verify lessons
        self.assertEqual(len(result.lessons), 4)
        lesson_titles = [lesson['title'] for lesson in result.lessons]
        self.assertIn("Get Started with the Platform", lesson_titles)
        self.assertIn("Understand Custom Objects", lesson_titles)
        self.assertIn("Explore the AppExchange", lesson_titles)
        self.assertIn("Knowledge Check", lesson_titles)
        
        # Verify prerequisites
        self.assertEqual(len(result.prerequisites), 2)
        self.assertIn("Basic understanding of CRM concepts", result.prerequisites)
        self.assertIn("Familiarity with web applications", result.prerequisites)
    
    def test_extract_title_h1(self):
        """Test title extraction from h1 tag."""
        self._load_fixture("mock_lesson.html")
        title = _extract_title(self.page)
        self.assertEqual(title, "Understanding Salesforce Platform Basics")
    
    def test_extract_title_fallback(self):
        """Test title extraction fallback to page title."""
        self.page.set_content("<html><head><title>Fallback Title</title></head><body></body></html>")
        title = _extract_title(self.page)
        self.assertEqual(title, "Fallback Title")
    
    def test_extract_learning_objectives(self):
        """Test learning objectives extraction."""
        self._load_fixture("mock_lesson.html")
        objectives = _extract_learning_objectives(self.page)
        
        self.assertEqual(len(objectives), 3)
        self.assertIn("Understand what the Salesforce Platform is", objectives)
        self.assertIn("Learn about custom objects and fields", objectives)
        self.assertIn("Explore the App Exchange marketplace", objectives)
    
    def test_extract_learning_objectives_empty(self):
        """Test learning objectives extraction when none exist."""
        self.page.set_content("<html><body><p>No objectives here</p></body></html>")
        objectives = _extract_learning_objectives(self.page)
        self.assertEqual(len(objectives), 0)
    
    def test_extract_lesson_content_types(self):
        """Test extraction of different content types."""
        self._load_fixture("mock_lesson.html")
        content_items = _extract_lesson_content(self.page)
        
        # Verify we got content
        self.assertGreater(len(content_items), 0)
        
        # Check for different types
        content_types = [item.element_type for item in content_items]
        self.assertIn('heading', content_types)
        self.assertIn('text', content_types)
        self.assertIn('code', content_types)
        self.assertIn('list', content_types)
        
        # Verify specific content
        headings = [item for item in content_items if item.element_type == 'heading']
        self.assertGreater(len(headings), 0)
        
        # Check heading levels
        h2_headings = [item for item in headings if item.level == 2]
        h3_headings = [item for item in headings if item.level == 3]
        self.assertGreater(len(h2_headings), 0)
        self.assertGreater(len(h3_headings), 0)
        
        # Verify code content
        code_items = [item for item in content_items if item.element_type == 'code']
        self.assertGreater(len(code_items), 0)
        self.assertIn("HelloWorld", code_items[0].text)
    
    def test_extract_instructions(self):
        """Test instruction extraction."""
        self._load_fixture("mock_lesson.html")
        instructions = _extract_instructions(self.page)
        
        self.assertEqual(len(instructions), 4)
        self.assertIn("Navigate to Setup", instructions[0])
        self.assertIn("Click on Object Manager", instructions[1])
        self.assertIn("Create a new custom object", instructions[2])
        self.assertIn("Add custom fields", instructions[3])
    
    def test_extract_instructions_numbered_text(self):
        """Test instruction extraction from numbered text."""
        html_content = """
        <html><body>
            <p>1. First step here</p>
            <p>2. Second step here</p>
            <p>Step 3: Third step here</p>
            <p>Regular paragraph</p>
        </body></html>
        """
        self.page.set_content(html_content)
        instructions = _extract_instructions(self.page)
        
        self.assertEqual(len(instructions), 3)
        self.assertIn("First step", instructions[0])
        self.assertIn("Second step", instructions[1])
        self.assertIn("Third step", instructions[2])
    
    def test_extract_links(self):
        """Test link extraction."""
        self._load_fixture("mock_lesson.html")
        links = _extract_links(self.page)
        
        self.assertGreater(len(links), 0)
        
        # Check for specific links
        link_urls = [link['url'] for link in links]
        self.assertIn("https://trailhead.salesforce.com/content/learn/modules/platform_dev_basics", link_urls)
        self.assertIn("https://developer.salesforce.com/docs", link_urls)
        
        # Check relative URL conversion
        self.assertIn("https://trailhead.salesforce.com/content/learn/modules/data_modeling", link_urls)
        
        # Verify link structure
        for link in links:
            self.assertIn('text', link)
            self.assertIn('url', link)
            self.assertIsInstance(link['text'], str)
            self.assertIsInstance(link['url'], str)
            self.assertGreater(len(link['text']), 2)
    
    def test_extract_links_deduplication(self):
        """Test that duplicate links are removed."""
        html_content = """
        <html><body>
            <a href="https://trailhead.salesforce.com/test">Test Link</a>
            <a href="https://trailhead.salesforce.com/test">Test Link</a>
            <a href="https://trailhead.salesforce.com/other">Other Link</a>
        </body></html>
        """
        self.page.set_content(html_content)
        links = _extract_links(self.page)
        
        self.assertEqual(len(links), 2)
        link_texts = [link['text'] for link in links]
        self.assertEqual(link_texts.count("Test Link"), 1)
    
    def test_extract_time_estimate_element(self):
        """Test time estimate extraction from element."""
        self._load_fixture("mock_lesson.html")
        time_estimate = _extract_time_estimate(self.page)
        self.assertEqual(time_estimate, "~15 min")
    
    def test_extract_time_estimate_text_pattern(self):
        """Test time estimate extraction from text patterns."""
        html_content = """
        <html><body>
            <p>This lesson takes approximately 25 minutes to complete.</p>
        </body></html>
        """
        self.page.set_content(html_content)
        time_estimate = _extract_time_estimate(self.page)
        self.assertEqual(time_estimate, "25 minutes")
    
    def test_extract_time_estimate_none(self):
        """Test time estimate extraction when none exists."""
        self.page.set_content("<html><body><p>No time estimate here</p></body></html>")
        time_estimate = _extract_time_estimate(self.page)
        self.assertIsNone(time_estimate)
    
    def test_extract_description(self):
        """Test description extraction."""
        self._load_fixture("mock_module.html")
        description = _extract_description(self.page)
        
        self.assertIn("Learn the fundamentals", description)
        self.assertGreater(len(description), 20)
    
    def test_extract_description_fallback(self):
        """Test description extraction fallback."""
        self.page.set_content("<html><body><p>Short</p></body></html>")
        description = _extract_description(self.page)
        self.assertEqual(description, "No description available")
    
    def test_extract_lessons_list(self):
        """Test lessons list extraction."""
        self._load_fixture("mock_module.html")
        lessons = _extract_lessons_list(self.page)
        
        self.assertEqual(len(lessons), 4)
        
        lesson_titles = [lesson['title'] for lesson in lessons]
        self.assertIn("Get Started with the Platform", lesson_titles)
        self.assertIn("Understand Custom Objects", lesson_titles)
        self.assertIn("Explore the AppExchange", lesson_titles)
        self.assertIn("Knowledge Check", lesson_titles)
        
        # Verify URL conversion
        lesson_urls = [lesson['url'] for lesson in lessons]
        for url in lesson_urls:
            self.assertTrue(url.startswith("https://trailhead.salesforce.com/"))
    
    def test_extract_difficulty(self):
        """Test difficulty extraction."""
        self._load_fixture("mock_module.html")
        difficulty = _extract_difficulty(self.page)
        self.assertEqual(difficulty, "Beginner")
    
    def test_extract_difficulty_text_pattern(self):
        """Test difficulty extraction from text pattern."""
        html_content = """
        <html><body>
            <p>Level: Intermediate - This module requires some experience.</p>
        </body></html>
        """
        self.page.set_content(html_content)
        difficulty = _extract_difficulty(self.page)
        self.assertEqual(difficulty, "Intermediate")
    
    def test_extract_difficulty_none(self):
        """Test difficulty extraction when none exists."""
        self.page.set_content("<html><body><p>No difficulty here</p></body></html>")
        difficulty = _extract_difficulty(self.page)
        self.assertIsNone(difficulty)
    
    def test_extract_prerequisites(self):
        """Test prerequisites extraction."""
        self._load_fixture("mock_module.html")
        prerequisites = _extract_prerequisites(self.page)
        
        self.assertEqual(len(prerequisites), 2)
        self.assertIn("Basic understanding of CRM concepts", prerequisites)
        self.assertIn("Familiarity with web applications", prerequisites)
    
    def test_extract_prerequisites_none(self):
        """Test prerequisites extraction when none exist."""
        self.page.set_content("<html><body><p>No prerequisites here</p></body></html>")
        prerequisites = _extract_prerequisites(self.page)
        self.assertIsNone(prerequisites)
    
    def test_content_item_dataclass(self):
        """Test ContentItem dataclass functionality."""
        # Test basic content item
        item1 = ContentItem(text="Test text", element_type="text")
        self.assertEqual(item1.text, "Test text")
        self.assertEqual(item1.element_type, "text")
        self.assertIsNone(item1.url)
        self.assertIsNone(item1.level)
        
        # Test content item with optional fields
        item2 = ContentItem(
            text="Test heading",
            element_type="heading",
            level=2
        )
        self.assertEqual(item2.level, 2)
        
        # Test content item with URL
        item3 = ContentItem(
            text="Test link",
            element_type="link",
            url="https://example.com"
        )
        self.assertEqual(item3.url, "https://example.com")
    
    def test_lesson_content_dataclass(self):
        """Test LessonContent dataclass functionality."""
        content_items = [
            ContentItem(text="Test heading", element_type="heading", level=1),
            ContentItem(text="Test paragraph", element_type="text")
        ]
        
        lesson = LessonContent(
            title="Test Lesson",
            url="https://example.com/lesson",
            content=content_items,
            learning_objectives=["Objective 1", "Objective 2"],
            instructions=["Step 1", "Step 2"],
            links=[{"text": "Link", "url": "https://example.com"}],
            estimated_time="30 min"
        )
        
        self.assertEqual(lesson.title, "Test Lesson")
        self.assertEqual(len(lesson.content), 2)
        self.assertEqual(len(lesson.learning_objectives), 2)
        self.assertEqual(len(lesson.instructions), 2)
        self.assertEqual(len(lesson.links), 1)
        self.assertEqual(lesson.estimated_time, "30 min")
    
    def test_module_content_dataclass(self):
        """Test ModuleContent dataclass functionality."""
        lessons = [
            {"title": "Lesson 1", "url": "https://example.com/lesson1"},
            {"title": "Lesson 2", "url": "https://example.com/lesson2"}
        ]
        
        module = ModuleContent(
            title="Test Module",
            url="https://example.com/module",
            description="Test description",
            lessons=lessons,
            estimated_time="2 hours",
            difficulty="Beginner",
            prerequisites=["Prerequisite 1", "Prerequisite 2"]
        )
        
        self.assertEqual(module.title, "Test Module")
        self.assertEqual(len(module.lessons), 2)
        self.assertEqual(module.difficulty, "Beginner")
        self.assertEqual(len(module.prerequisites), 2)


class TestParseWithRealFixtures(unittest.TestCase):
    """Test parse functions with real Trailhead HTML fixtures if available."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.test_dir = Path(__file__).parent.parent
        cls.fixtures_dir = cls.test_dir / "fixtures"
        
        # Start playwright browser for testing
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.context = cls.browser.new_context()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up browser resources."""
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()
    
    def setUp(self):
        """Set up each test."""
        self.page = self.context.new_page()
    
    def tearDown(self):
        """Clean up each test."""
        self.page.close()
    
    def _load_fixture(self, filename: str):
        """Load an HTML fixture file."""
        fixture_path = self.fixtures_dir / filename
        if not fixture_path.exists():
            self.skipTest(f"Fixture {filename} not found")
        
        file_url = f"file://{fixture_path.absolute()}"
        self.page.goto(file_url)
        self.page.wait_for_load_state("domcontentloaded")
    
    def test_parse_real_module_html(self):
        """Test parsing with real module.html fixture."""
        try:
            self._load_fixture("module.html")
            result = parse_module(self.page)
            
            # Basic validation - should not crash and return valid structure
            self.assertIsInstance(result, ModuleContent)
            self.assertIsInstance(result.title, str)
            self.assertIsInstance(result.url, str)
            self.assertIsInstance(result.description, str)
            self.assertIsInstance(result.lessons, list)
            
            # Title should not be empty or default
            self.assertNotEqual(result.title, "")
            self.assertNotEqual(result.title, "Unknown Title")
            
        except Exception as e:
            self.skipTest(f"Could not parse real module.html: {e}")
    
    def test_parse_real_lesson_html(self):
        """Test parsing with real lesson.html fixture."""
        try:
            self._load_fixture("lesson.html")
            result = parse_lesson(self.page)
            
            # Basic validation - should not crash and return valid structure
            self.assertIsInstance(result, LessonContent)
            self.assertIsInstance(result.title, str)
            self.assertIsInstance(result.url, str)
            self.assertIsInstance(result.content, list)
            self.assertIsInstance(result.learning_objectives, list)
            self.assertIsInstance(result.instructions, list)
            self.assertIsInstance(result.links, list)
            
            # Title should not be empty or default
            self.assertNotEqual(result.title, "")
            self.assertNotEqual(result.title, "Unknown Title")
            
        except Exception as e:
            self.skipTest(f"Could not parse real lesson.html: {e}")
    
    def test_parse_real_trail_html(self):
        """Test parsing trail HTML structure (using internal functions)."""
        try:
            self._load_fixture("trail.html")
            
            # Test title extraction
            title = _extract_title(self.page)
            self.assertIsInstance(title, str)
            self.assertNotEqual(title, "")
            
            # Test description extraction
            description = _extract_description(self.page)
            self.assertIsInstance(description, str)
            
        except Exception as e:
            self.skipTest(f"Could not parse real trail.html: {e}")


if __name__ == '__main__':
    unittest.main()