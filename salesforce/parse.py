import re
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page
from dataclasses import dataclass


@dataclass
class ContentItem:
    """Represents a piece of content extracted from a page."""
    text: str
    element_type: str  # 'text', 'link', 'code', 'list', 'heading'
    url: Optional[str] = None  # For links
    level: Optional[int] = None  # For headings


@dataclass
class LessonContent:
    """Structure for lesson content."""
    title: str
    url: str
    content: List[ContentItem]
    learning_objectives: List[str]
    instructions: List[str]
    links: List[Dict[str, str]]
    estimated_time: Optional[str] = None


@dataclass
class ModuleContent:
    """Structure for module content."""
    title: str
    url: str
    description: str
    lessons: List[Dict[str, str]]  # List of lesson titles and URLs
    estimated_time: Optional[str] = None
    difficulty: Optional[str] = None
    prerequisites: List[str] = None


def parse_lesson(page: Page) -> LessonContent:
    """
    Parse a Trailhead lesson page to extract relevant content for LLM processing.
    
    Args:
        page: Playwright page object
        
    Returns:
        LessonContent object with extracted information
    """
    content_items = []
    learning_objectives = []
    instructions = []
    links = []
    
    # Extract title
    title = _extract_title(page)
    
    # Extract learning objectives
    learning_objectives = _extract_learning_objectives(page)
    
    # Extract main content
    content_items = _extract_lesson_content(page)
    
    # Extract instructions/steps
    instructions = _extract_instructions(page)
    
    # Extract links
    links = _extract_links(page)
    
    # Extract estimated time
    estimated_time = _extract_time_estimate(page)
    
    return LessonContent(
        title=title,
        url=page.url,
        content=content_items,
        learning_objectives=learning_objectives,
        instructions=instructions,
        links=links,
        estimated_time=estimated_time
    )


def parse_module(page: Page) -> ModuleContent:
    """
    Parse a Trailhead module page to extract module overview and lesson links.
    
    Args:
        page: Playwright page object
        
    Returns:
        ModuleContent object with extracted information
    """
    # Extract title
    title = _extract_title(page)
    
    # Extract description
    description = _extract_description(page)
    
    # Extract lessons list
    lessons = _extract_lessons_list(page)
    
    # Extract metadata
    estimated_time = _extract_time_estimate(page)
    difficulty = _extract_difficulty(page)
    prerequisites = _extract_prerequisites(page)
    
    return ModuleContent(
        title=title,
        url=page.url,
        description=description,
        lessons=lessons,
        estimated_time=estimated_time,
        difficulty=difficulty,
        prerequisites=prerequisites or []
    )


def _extract_title(page: Page) -> str:
    """Extract the page title."""
    selectors = [
        "h1",
        "[data-testid='module-title']",
        "[data-testid='lesson-title']",
        ".module-title",
        ".lesson-title",
        ".trailhead-title"
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                return element.text_content().strip()
        except:
            continue
    
    # Fallback to page title
    try:
        return page.title() or "Unknown Title"
    except:
        return "Unknown Title"


def _extract_learning_objectives(page: Page) -> List[str]:
    """Extract learning objectives from the page."""
    objectives = []
    
    # Common selectors for learning objectives
    selectors = [
        "[data-testid='learning-objectives'] li",
        ".learning-objectives li",
        ".objectives li",
        "h2:has-text('Learning Objectives') + ul li",
        "h3:has-text('Learning Objectives') + ul li",
        "h2:has-text('Objectives') + ul li",
        "h3:has-text('Objectives') + ul li"
    ]
    
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                objectives = [elem.text_content().strip() for elem in elements if elem.text_content().strip()]
                if objectives:
                    break
        except:
            continue
    
    return objectives


def _extract_lesson_content(page: Page) -> List[ContentItem]:
    """Extract main lesson content."""
    content_items = []
    
    # Main content area selectors
    content_selectors = [
        "main",
        ".lesson-content",
        ".module-content",
        ".trailhead-content",
        "[role='main']",
        ".content-body"
    ]
    
    content_container = None
    for selector in content_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                content_container = element
                break
        except:
            continue
    
    if not content_container:
        # Fallback to body
        content_container = page.locator("body")
    
    # Extract different types of content
    try:
        # Extract headings
        for level in range(1, 7):
            headings = content_container.locator(f"h{level}").all()
            for heading in headings:
                text = heading.text_content().strip()
                if text and len(text) > 3:  # Filter out very short headings
                    content_items.append(ContentItem(
                        text=text,
                        element_type='heading',
                        level=level
                    ))
        
        # Extract paragraphs
        paragraphs = content_container.locator("p").all()
        for p in paragraphs:
            text = p.text_content().strip()
            if text and len(text) > 10:  # Filter out very short paragraphs
                content_items.append(ContentItem(
                    text=text,
                    element_type='text'
                ))
        
        # Extract code blocks
        code_blocks = content_container.locator("pre, code, .code-block").all()
        for code in code_blocks:
            text = code.text_content().strip()
            if text:
                content_items.append(ContentItem(
                    text=text,
                    element_type='code'
                ))
        
        # Extract lists
        lists = content_container.locator("ul, ol").all()
        for list_elem in lists:
            items = list_elem.locator("li").all()
            if items:
                list_text = "\n".join([item.text_content().strip() for item in items if item.text_content().strip()])
                if list_text:
                    content_items.append(ContentItem(
                        text=list_text,
                        element_type='list'
                    ))
    
    except Exception as e:
        print(f"Error extracting lesson content: {e}")
    
    return content_items


def _extract_instructions(page: Page) -> List[str]:
    """Extract step-by-step instructions."""
    instructions = []
    
    # Common selectors for instructions
    selectors = [
        ".instructions li",
        ".steps li",
        ".step-list li",
        "[data-testid='instructions'] li",
        "ol.instructions li",
        "ol.steps li",
        ".numbered-list li"
    ]
    
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                instructions = [elem.text_content().strip() for elem in elements if elem.text_content().strip()]
                if instructions:
                    break
        except:
            continue
    
    # If no structured instructions found, look for numbered steps in text
    if not instructions:
        try:
            # Look for numbered steps in paragraphs
            paragraphs = page.locator("p").all()
            for p in paragraphs:
                text = p.text_content().strip()
                # Match patterns like "1. Step one", "Step 1:", etc.
                if re.match(r'^\d+\.?\s+', text) or re.match(r'^Step\s+\d+', text, re.IGNORECASE):
                    instructions.append(text)
        except:
            pass
    
    return instructions


def _extract_links(page: Page) -> List[Dict[str, str]]:
    """Extract relevant links from the page."""
    links = []
    
    try:
        # Get all links
        link_elements = page.locator("a[href]").all()
        
        for link in link_elements:
            try:
                href = link.get_attribute("href")
                text = link.text_content().strip()
                
                if href and text and len(text) > 2:
                    # Filter for relevant links (Trailhead, documentation, etc.)
                    if any(domain in href for domain in [
                        'trailhead.salesforce.com',
                        'developer.salesforce.com',
                        'help.salesforce.com',
                        'salesforce.com/products',
                        'github.com',
                        'docs.salesforce.com'
                    ]) or href.startswith('/'):
                        
                        # Make relative URLs absolute
                        if href.startswith('/'):
                            href = f"https://trailhead.salesforce.com{href}"
                        
                        links.append({
                            'text': text,
                            'url': href
                        })
            except:
                continue
    
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    # Remove duplicates
    seen = set()
    unique_links = []
    for link in links:
        key = (link['text'], link['url'])
        if key not in seen:
            seen.add(key)
            unique_links.append(link)
    
    return unique_links


def _extract_time_estimate(page: Page) -> Optional[str]:
    """Extract estimated completion time."""
    selectors = [
        "[data-testid='time-estimate']",
        ".time-estimate",
        ".duration",
        ".estimated-time"
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                return element.text_content().strip()
        except:
            continue
    
    # Look for time patterns in text
    try:
        text = page.locator("body").text_content()
        time_patterns = [
            r'(\d+)\s*(?:min|minute|minutes)',
            r'(\d+)\s*(?:hr|hour|hours)',
            r'~\s*(\d+)\s*(?:min|minute|minutes)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
    except:
        pass
    
    return None


def _extract_description(page: Page) -> str:
    """Extract module description."""
    selectors = [
        "[data-testid='module-description']",
        ".module-description",
        ".description",
        ".module-intro",
        "p:first-of-type"
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                text = element.text_content().strip()
                if text and len(text) > 20:  # Ensure it's substantial
                    return text
        except:
            continue
    
    return "No description available"


def _extract_lessons_list(page: Page) -> List[Dict[str, str]]:
    """Extract list of lessons in a module."""
    lessons = []
    
    # Common selectors for lesson lists
    selectors = [
        ".lesson-list a",
        ".unit-list a",
        ".module-units a",
        "[data-testid='lesson-link']",
        ".lessons a",
        ".units a"
    ]
    
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                for elem in elements:
                    href = elem.get_attribute("href")
                    text = elem.text_content().strip()
                    
                    if href and text:
                        # Make relative URLs absolute
                        if href.startswith('/'):
                            href = f"https://trailhead.salesforce.com{href}"
                        
                        lessons.append({
                            'title': text,
                            'url': href
                        })
                
                if lessons:
                    break
        except:
            continue
    
    return lessons


def _extract_difficulty(page: Page) -> Optional[str]:
    """Extract difficulty level."""
    selectors = [
        "[data-testid='difficulty']",
        ".difficulty",
        ".level"
    ]
    
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                return element.text_content().strip()
        except:
            continue
    
    # Look for difficulty patterns in text
    try:
        text = page.locator("body").text_content()
        difficulty_patterns = [
            r'(Beginner|Intermediate|Advanced)',
            r'Level:\s*(Beginner|Intermediate|Advanced)'
        ]
        
        for pattern in difficulty_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
    except:
        pass
    
    return None


def _extract_prerequisites(page: Page) -> Optional[List[str]]:
    """Extract prerequisites."""
    prerequisites = []
    
    # Look for prerequisites section
    selectors = [
        "h2:has-text('Prerequisites') + ul li",
        "h3:has-text('Prerequisites') + ul li",
        ".prerequisites li",
        "[data-testid='prerequisites'] li"
    ]
    
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                prerequisites = [elem.text_content().strip() for elem in elements if elem.text_content().strip()]
                if prerequisites:
                    break
        except:
            continue
    
    return prerequisites if prerequisites else None