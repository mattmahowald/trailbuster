"""Test data and fixtures for TrailBuster tests."""

from salesforce.parse import ContentItem, LessonContent, ModuleContent

# Sample content items
SAMPLE_CONTENT_ITEMS = [
    ContentItem(text="Introduction to Salesforce", element_type="heading", level=1),
    ContentItem(
        text="Salesforce is a cloud-based CRM platform that helps businesses manage customer relationships.",
        element_type="text",
    ),
    ContentItem(text="Key Features", element_type="heading", level=2),
    ContentItem(
        text="Lead management\nOpportunity tracking\nCustomer service",
        element_type="list",
    ),
    ContentItem(
        text="public class Account {\n    public String name;\n}", element_type="code"
    ),
    ContentItem(text="Getting Started", element_type="heading", level=2),
    ContentItem(
        text="To begin using Salesforce, you'll need to understand the basic concepts and navigation.",
        element_type="text",
    ),
]

# Sample learning objectives
SAMPLE_LEARNING_OBJECTIVES = [
    "Understand what Salesforce is and how it works",
    "Learn about key Salesforce features and capabilities",
    "Navigate the Salesforce user interface",
    "Create and manage basic records",
    "Use reports and dashboards",
]

# Sample instructions
SAMPLE_INSTRUCTIONS = [
    "Log into your Salesforce org using your credentials",
    "Navigate to the Setup menu by clicking the gear icon",
    "Find the Object Manager in the Platform Tools section",
    "Create a new custom object by clicking 'Create' > 'Custom Object'",
    "Configure the object settings and save your changes",
]

# Sample links
SAMPLE_LINKS = [
    {"text": "Salesforce Help Documentation", "url": "https://help.salesforce.com"},
    {
        "text": "Trailhead Learning Path",
        "url": "https://trailhead.salesforce.com/content/learn/trails/force_com_admin_beginner",
    },
    {"text": "Developer Documentation", "url": "https://developer.salesforce.com/docs"},
    {
        "text": "Community Forums",
        "url": "https://trailhead.salesforce.com/trailblazer-community",
    },
]

# Sample lesson content
SAMPLE_LESSON_CONTENT = LessonContent(
    title="Understanding the Salesforce Platform",
    url="https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_intro",
    content=SAMPLE_CONTENT_ITEMS,
    learning_objectives=SAMPLE_LEARNING_OBJECTIVES,
    instructions=SAMPLE_INSTRUCTIONS,
    links=SAMPLE_LINKS,
    estimated_time="30 min",
)

# Sample module lessons
SAMPLE_MODULE_LESSONS = [
    {
        "title": "Get Started with the Platform",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_intro",
    },
    {
        "title": "Understand Custom Objects",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_understanding_custom_objects",
    },
    {
        "title": "Explore the AppExchange",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_understanding_appexchange",
    },
    {
        "title": "Knowledge Check",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_quiz",
    },
]

# Sample module content
SAMPLE_MODULE_CONTENT = ModuleContent(
    title="Salesforce Platform Basics",
    url="https://trailhead.salesforce.com/content/learn/modules/starting_force_com",
    description="Learn the fundamentals of the Salesforce Platform, including custom objects, workflows, and the App Exchange marketplace.",
    lessons=SAMPLE_MODULE_LESSONS,
    estimated_time="2 hours",
    difficulty="Beginner",
    prerequisites=[
        "Basic understanding of CRM concepts",
        "Familiarity with web applications",
    ],
)

# Sample trail modules
SAMPLE_TRAIL_MODULES = [
    {
        "title": "Salesforce Platform Basics",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com",
    },
    {
        "title": "Data Modeling",
        "url": "https://trailhead.salesforce.com/content/learn/modules/data_modeling",
    },
    {
        "title": "Lightning Experience Basics",
        "url": "https://trailhead.salesforce.com/content/learn/modules/lex_migration_introduction",
    },
    {
        "title": "User Management",
        "url": "https://trailhead.salesforce.com/content/learn/modules/lex_implementation_user_setup_mgmt",
    },
]

# Sample trail info
SAMPLE_TRAIL_INFO = {
    "title": "Force.com Admin Beginner",
    "description": "Get started as a Salesforce administrator with this comprehensive trail covering all the basics.",
    "url": "https://trailhead.salesforce.com/trails/force_com_admin_beginner",
    "modules": SAMPLE_TRAIL_MODULES,
}

# Sample crawl results
SAMPLE_MODULE_CRAWL_RESULT = {
    "module": {
        "title": "Salesforce Platform Basics",
        "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com",
        "description": "Learn the fundamentals of the Salesforce Platform, including custom objects, workflows, and the App Exchange marketplace.",
        "lessons": SAMPLE_MODULE_LESSONS,
        "estimated_time": "2 hours",
        "difficulty": "Beginner",
        "prerequisites": [
            "Basic understanding of CRM concepts",
            "Familiarity with web applications",
        ],
    },
    "lessons": [
        {
            "title": "Understanding the Salesforce Platform",
            "url": "https://trailhead.salesforce.com/content/learn/modules/starting_force_com/starting_force_com_intro",
            "content": [
                {
                    "text": "Introduction to Salesforce",
                    "element_type": "heading",
                    "url": None,
                    "level": 1,
                },
                {
                    "text": "Salesforce is a cloud-based CRM platform that helps businesses manage customer relationships.",
                    "element_type": "text",
                    "url": None,
                    "level": None,
                },
            ],
            "learning_objectives": SAMPLE_LEARNING_OBJECTIVES,
            "instructions": SAMPLE_INSTRUCTIONS,
            "links": SAMPLE_LINKS,
            "estimated_time": "30 min",
        }
    ],
    "crawl_timestamp": 1234567890,
    "crawl_date": "2023-01-01 12:00:00",
}

SAMPLE_TRAIL_CRAWL_RESULT = {
    "trail": SAMPLE_TRAIL_INFO,
    "modules": [SAMPLE_MODULE_CRAWL_RESULT],
    "crawl_timestamp": 1234567890,
    "crawl_date": "2023-01-01 12:00:00",
}

# HTML templates for testing
MINIMAL_LESSON_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Lesson</title></head>
<body>
    <h1>Test Lesson Title</h1>
    <div class="learning-objectives">
        <ul>
            <li>Learn basic concepts</li>
            <li>Practice skills</li>
        </ul>
    </div>
    <div class="content-body">
        <p>This is the main lesson content.</p>
        <h2>Section 1</h2>
        <p>Section content here.</p>
    </div>
    <ol class="instructions">
        <li>Step one</li>
        <li>Step two</li>
    </ol>
    <div class="time-estimate">25 min</div>
</body>
</html>
"""

MINIMAL_MODULE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Module</title></head>
<body>
    <h1>Test Module Title</h1>
    <div class="module-description">
        <p>This is a test module description with sufficient length to be meaningful.</p>
    </div>
    <div class="lessons">
        <a href="/content/learn/modules/test/lesson1">Lesson 1</a>
        <a href="/content/learn/modules/test/lesson2">Lesson 2</a>
    </div>
    <div class="time-estimate">1 hour</div>
    <div class="difficulty">Intermediate</div>
    <div class="prerequisites">
        <ul>
            <li>Basic knowledge required</li>
        </ul>
    </div>
</body>
</html>
"""

MINIMAL_TRAIL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Trail</title></head>
<body>
    <h1>Test Trail Title</h1>
    <div class="trail-description">
        <p>This is a test trail description with comprehensive learning path.</p>
    </div>
    <div class="modules-list">
        <a href="/content/learn/modules/module1">Module 1</a>
        <a href="/content/learn/modules/module2">Module 2</a>
        <a href="/content/learn/modules/module3">Module 3</a>
    </div>
</body>
</html>
"""

# Error HTML templates
ERROR_HTML = """
<!DOCTYPE html>
<html>
<head><title>Page Not Found</title></head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The requested page could not be found.</p>
</body>
</html>
"""

EMPTY_HTML = """
<!DOCTYPE html>
<html>
<head><title>Empty Page</title></head>
<body></body>
</html>
"""


def create_test_html_file(html_content: str, filename: str, directory: str) -> str:
    """Create a test HTML file with the given content.

    Args:
        html_content: HTML content to write
        filename: Name of the file to create
        directory: Directory to create the file in

    Returns:
        Path to the created file
    """
    import os
    from pathlib import Path

    file_path = Path(directory) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(file_path)


def get_sample_urls_content() -> str:
    """Get sample URLs file content for testing."""
    return """# Sample URLs for testing
https://trailhead.salesforce.com/content/learn/modules/starting_force_com
https://trailhead.salesforce.com/content/learn/modules/data_modeling
https://trailhead.salesforce.com/trails/force_com_admin_beginner

# Comments and empty lines should be ignored

https://trailhead.salesforce.com/content/learn/modules/lightning_experience_basics
"""
