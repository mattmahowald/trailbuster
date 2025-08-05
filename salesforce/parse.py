"""
Content parsing functions for Trailhead pages.

This module provides structured parsing functions to extract LLM-ready content
from Trailhead module and lesson pages.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from playwright.sync_api import Page

from trailbuster.logger import get_logger, log_parser, log_link_extraction


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
    """Parse a lesson page and extract structured content."""
    logger = get_logger("PARSER")
    logger.start_operation("lesson_parsing", url=page.url)

    try:
        title = _extract_title(page)
        learning_objectives = _extract_learning_objectives(page)
        content = _extract_lesson_content(page)
        instructions = _extract_instructions(page)
        links = _extract_links(page)
        estimated_time = _extract_time_estimate(page)

        lesson_content = LessonContent(
            title=title,
            url=page.url,
            content=content,
            learning_objectives=learning_objectives,
            instructions=instructions,
            links=links,
            estimated_time=estimated_time,
        )

        logger.info(
            f"Lesson parsed successfully: {title}",
            {
                "content_items": len(content),
                "learning_objectives": len(learning_objectives),
                "instructions": len(instructions),
                "links": len(links),
                "estimated_time": estimated_time,
            },
        )

        logger.end_operation("lesson_parsing", success=True, lesson_title=title)
        return lesson_content

    except Exception as e:
        logger.error(f"Error parsing lesson: {e}")
        logger.end_operation("lesson_parsing", success=False, error=str(e))
        raise


def parse_module(page: Page) -> ModuleContent:
    """Parse a module page and extract structured content."""
    logger = get_logger("PARSER")
    logger.start_operation("module_parsing", url=page.url)

    try:
        title = _extract_title(page)
        description = _extract_description(page)
        lessons = _extract_lessons_list(page)
        estimated_time = _extract_time_estimate(page)
        difficulty = _extract_difficulty(page)
        prerequisites = _extract_prerequisites(page)

        module_content = ModuleContent(
            title=title,
            url=page.url,
            description=description,
            lessons=lessons,
            estimated_time=estimated_time,
            difficulty=difficulty,
            prerequisites=prerequisites or [],
        )

        logger.info(
            f"Module parsed successfully: {title}",
            {
                "description_length": len(description),
                "lessons_count": len(lessons),
                "estimated_time": estimated_time,
                "difficulty": difficulty,
                "prerequisites_count": len(prerequisites or []),
            },
        )

        logger.end_operation("module_parsing", success=True, module_title=title)
        return module_content

    except Exception as e:
        logger.error(f"Error parsing module: {e}")
        logger.end_operation("module_parsing", success=False, error=str(e))
        raise


def _extract_title(page: Page) -> str:
    """Extract the title from the page."""
    selectors = [
        "h1",
        "[data-testid='lesson-title']",
        "[data-testid='module-title']",
        ".lesson-title",
        ".module-title",
        ".title",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                title = element.text_content().strip()
                if title and len(title) > 2:
                    return title
        except:
            continue

    return "Untitled"


def _extract_learning_objectives(page: Page) -> List[str]:
    """Extract learning objectives from the page."""
    objectives = []

    # Look for learning objectives section
    objective_selectors = [
        "[data-testid='learning-objectives']",
        ".learning-objectives",
        ".objectives",
        ".learning-goals",
    ]

    for selector in objective_selectors:
        try:
            container = page.locator(selector).first
            if container.is_visible():
                # Look for list items within the container
                items = container.locator("li, .objective-item, .goal-item").all()
                for item in items:
                    text = item.text_content().strip()
                    if text and len(text) > 5:
                        objectives.append(text)

                if objectives:
                    break
        except:
            continue

    # If no structured objectives found, look for common patterns
    if not objectives:
        try:
            page_text = page.locator("body").text_content()
            # Look for patterns like "You'll learn to..." or "In this lesson..."
            patterns = [
                r"You'll learn to[^.]*\.?",
                r"In this lesson[^.]*\.?",
                r"Learning objectives[^.]*\.?",
                r"By the end of this[^.]*\.?",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                objectives.extend(matches)
        except:
            pass

    return objectives


def _extract_lesson_content(page: Page) -> List[ContentItem]:
    """Extract structured content from the lesson page."""
    content_items = []
    logger = get_logger("PARSER")

    try:
        # Main content area selectors
        content_selectors = [
            "[data-testid='lesson-content']",
            ".lesson-content",
            ".content",
            ".main-content",
            "main",
            ".lesson-body",
        ]

        content_container = None
        for selector in content_selectors:
            try:
                container = page.locator(selector).first
                if container.is_visible():
                    content_container = container
                    break
            except:
                continue

        if not content_container:
            # Fallback to body if no specific content container found
            content_container = page.locator("body")

        # Extract headings
        headings = content_container.locator("h1, h2, h3, h4, h5, h6").all()
        for heading in headings:
            try:
                text = heading.text_content().strip()
                if text and len(text) > 2:
                    level = int(heading.tag_name[1])  # Extract level from h1, h2, etc.
                    content_items.append(
                        ContentItem(text=text, element_type="heading", level=level)
                    )
            except:
                continue

        # Extract paragraphs
        paragraphs = content_container.locator("p").all()
        for p in paragraphs:
            try:
                text = p.text_content().strip()
                if text and len(text) > 10:  # Filter out very short paragraphs
                    content_items.append(ContentItem(text=text, element_type="text"))
            except:
                continue

        # Extract code blocks
        code_blocks = content_container.locator("pre, code, .code-block").all()
        for code in code_blocks:
            try:
                text = code.text_content().strip()
                if text and len(text) > 5:
                    content_items.append(ContentItem(text=text, element_type="code"))
            except:
                continue

        # Extract lists
        lists = content_container.locator("ul, ol").all()
        for list_elem in lists:
            try:
                items = list_elem.locator("li").all()
                list_text = []
                for item in items:
                    text = item.text_content().strip()
                    if text:
                        list_text.append(text)

                if list_text:
                    combined_text = "\n".join([f"• {item}" for item in list_text])
                    content_items.append(
                        ContentItem(text=combined_text, element_type="list")
                    )
            except:
                continue

        logger.info(f"Extracted {len(content_items)} content items from lesson")
        return content_items

    except Exception as e:
        logger.error(f"Error extracting lesson content: {e}")
        return content_items


def _extract_instructions(page: Page) -> List[str]:
    """Extract step-by-step instructions from the page."""
    instructions = []

    # Look for instruction sections
    instruction_selectors = [
        "[data-testid='instructions']",
        ".instructions",
        ".steps",
        ".procedure",
        ".how-to",
    ]

    for selector in instruction_selectors:
        try:
            container = page.locator(selector).first
            if container.is_visible():
                # Look for numbered or bulleted steps
                steps = container.locator("li, .step, .instruction-step").all()
                for step in steps:
                    text = step.text_content().strip()
                    if text and len(text) > 5:
                        instructions.append(text)

                if instructions:
                    break
        except:
            continue

    # If no structured instructions found, look for numbered patterns
    if not instructions:
        try:
            page_text = page.locator("body").text_content()
            # Look for numbered patterns like "1.", "Step 1:", etc.
            patterns = [
                r"\d+\.\s*[^.]*\.?",
                r"Step\s+\d+[^.]*\.?",
                r"\(\d+\)[^.]*\.?",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_text)
                instructions.extend(matches)
        except:
            pass

    return instructions


def _extract_links(page: Page) -> List[Dict[str, str]]:
    """Extract relevant links from the page."""
    links = []
    logger = get_logger("PARSER")

    logger.start_operation("link_extraction", url=page.url)

    try:
        # Get all links
        link_elements = page.locator("a[href]").all()
        total_links_found = len(link_elements)

        logger.debug(f"Found {total_links_found} total links on page")

        for link in link_elements:
            try:
                href = link.get_attribute("href")
                text = link.text_content().strip()

                if href and text and len(text) > 2:
                    # Filter for relevant links (Trailhead, documentation, etc.)
                    relevant_domains = [
                        "trailhead.salesforce.com",
                        "developer.salesforce.com",
                        "help.salesforce.com",
                        "salesforce.com/products",
                        "github.com",
                        "docs.salesforce.com",
                    ]

                    is_relevant = any(
                        domain in href for domain in relevant_domains
                    ) or href.startswith("/")

                    if is_relevant:
                        # Make relative URLs absolute
                        if href.startswith("/"):
                            href = f"https://trailhead.salesforce.com{href}"

                        links.append({"text": text, "url": href})
                        logger.debug(f"Extracted link: {text} -> {href}")
            except Exception as e:
                logger.debug(f"Error processing link element: {e}")
                continue

        # Remove duplicates
        seen = set()
        unique_links = []
        for link in links:
            key = (link["text"], link["url"])
            if key not in seen:
                seen.add(key)
                unique_links.append(link)

        logger.info(
            f"Link extraction completed",
            {
                "total_links_found": total_links_found,
                "relevant_links_extracted": len(links),
                "unique_links_final": len(unique_links),
                "extraction_rate": (
                    (len(unique_links) / total_links_found * 100)
                    if total_links_found > 0
                    else 0
                ),
            },
        )

        log_link_extraction(page.url, total_links_found, len(unique_links))
        logger.end_operation(
            "link_extraction", success=True, links_extracted=len(unique_links)
        )

        return unique_links

    except Exception as e:
        logger.error(f"Error extracting links: {e}")
        logger.end_operation("link_extraction", success=False, error=str(e))
        return []


def _extract_time_estimate(page: Page) -> Optional[str]:
    """Extract estimated completion time."""
    selectors = [
        "[data-testid='time-estimate']",
        ".time-estimate",
        ".duration",
        ".estimated-time",
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
            r"(\d+)\s*(?:min|minute|minutes)",
            r"(\d+)\s*(?:hr|hour|hours)",
            r"~\s*(\d+)\s*(?:min|minute|minutes)",
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
        "p:first-of-type",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                description = element.text_content().strip()
                if description and len(description) > 20:
                    return description
        except:
            continue

    return "No description available"


def _extract_lessons_list(page: Page) -> List[Dict[str, str]]:
    """Extract list of lessons from module page."""
    lessons = []
    seen_urls = set()  # Track seen URLs to avoid duplicates

    # Look for lesson links
    lesson_selectors = [
        "[data-testid='lesson-link']",
        ".lesson-link",
        ".lesson-item a",
        ".module-lessons a",
        "a[href*='/content/learn/modules/']",
    ]

    for selector in lesson_selectors:
        try:
            elements = page.locator(selector).all()
            if elements:
                for element in elements:
                    href = element.get_attribute("href")
                    text = element.text_content().strip()

                    if href and text and "modules" in href:
                        if href.startswith("/"):
                            href = f"https://trailhead.salesforce.com{href}"

                        # Skip if we've already seen this URL
                        if href in seen_urls:
                            continue

                        # Skip generic titles like "Start", "Incomplete", etc.
                        if text.lower() in ["start", "incomplete", "complete"]:
                            continue

                        lessons.append({"title": text, "url": href})
                        seen_urls.add(href)

                # If we found lessons with this selector, don't try others
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
        ".level",
        ".skill-level",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible():
                difficulty = element.text_content().strip()
                if difficulty:
                    return difficulty
        except:
            continue

    # Look for difficulty patterns in text
    try:
        text = page.locator("body").text_content()
        difficulty_patterns = [
            r"Beginner",
            r"Intermediate",
            r"Advanced",
            r"Expert",
        ]

        for pattern in difficulty_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
    except:
        pass

    return None


def _extract_prerequisites(page: Page) -> Optional[List[str]]:
    """Extract prerequisites."""
    prerequisites = []

    # Look for prerequisites section
    prereq_selectors = [
        "[data-testid='prerequisites']",
        ".prerequisites",
        ".requirements",
        ".pre-requisites",
    ]

    for selector in prereq_selectors:
        try:
            container = page.locator(selector).first
            if container.is_visible():
                items = container.locator("li, .prerequisite-item").all()
                for item in items:
                    text = item.text_content().strip()
                    if text and len(text) > 5:
                        prerequisites.append(text)

                if prerequisites:
                    break
        except:
            continue

    return prerequisites if prerequisites else None
