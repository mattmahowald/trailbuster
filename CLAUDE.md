# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
TrailBuster is a Python automation tool for Salesforce Trailhead that uses Playwright for browser automation and Gmail API for verification code retrieval. The project automates login to Salesforce Trailhead, handles two-factor authentication, and can read module content.

## Development Commands

### Installation and Setup
```bash
# Install Playwright browsers
python -m playwright install

# Install dependencies (Poetry is configured but pip install also works)
pip install playwright python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Running the Application
```bash
# Module Crawling
python main.py                                    # Crawl default module
python main.py <module_url>                       # Crawl specific module
python main.py trail <trail_url>                  # Crawl entire trail
python main.py batch <urls_file>                  # Batch crawl from file

# Options
python main.py stats                              # Show crawling statistics
python main.py --clear-session                    # Clear saved session
python main.py --no-session                       # Force new login
python main.py --help                             # Show detailed help

# Examples
python main.py https://trailhead.salesforce.com/content/learn/modules/starting_force_com
python main.py trail https://trailhead.salesforce.com/trails/force_com_admin_beginner
python main.py batch sample_urls.txt
```

## Architecture

### Core Components
- **Main Application** (`main.py`): Streamlined entry point for comprehensive Trailhead crawling
- **SalesforceAuth** (`salesforce/auth.py`): Main authentication class using dataclass pattern for results and organized selectors
- **TrailheadCrawler** (`crawl.py`): Comprehensive crawler for modules, lessons, and trails with progress tracking
- **Content Parsers** (`salesforce/parse.py`): Structured parsing functions for extracting LLM-ready content from Trailhead pages
- **Gmail Integration** (`salesforce/auth_code.py`): Clean Gmail API wrapper for verification code retrieval

### Key Design Patterns
- **Dataclass Pattern**: `LoginResult` dataclass for structured return values
- **Context Manager**: SalesforceAuth uses context manager pattern for resource cleanup
- **Selector Dictionary**: Organized selectors by purpose for better maintainability
- **Separation of Concerns**: Authentication, module reading, and Gmail integration are cleanly separated
- **Session Persistence**: Browser sessions are saved to `trailhead_session.json` to avoid repeated logins
- **Retry Logic**: Built-in retry mechanisms for network operations and element finding

### Authentication Flow
1. Check for existing valid session
2. Navigate to Trailhead login page
3. Enter email address
4. Handle reCAPTCHA if present (manual intervention)
5. Retrieve verification code from Gmail
6. Submit verification code
7. Save session for future use

### File Structure
```
├── main.py               # Unified entry point with integrated crawling functionality
├── crawl.py              # TrailheadCrawler class for comprehensive content extraction
├── sample_urls.txt       # Example URLs for batch crawling
├── salesforce/
│   ├── auth.py          # SalesforceAuth class with LoginResult dataclass
│   ├── auth_code.py     # Clean Gmail API integration
│   └── parse.py         # Content parsing functions with structured data classes
├── pyproject.toml       # Poetry configuration with dependencies
└── README.md           # Comprehensive setup and usage documentation
```

### Important Implementation Details
- **Streamlined Interface**: `main.py` provides a clean, focused entry point for comprehensive Trailhead crawling
- **LLM-Optimized Content**: All extracted content is structured specifically for LLM processing with:
  - Learning objectives and instructions
  - Content categorization (text, code, lists, headings)
  - Link extraction and validation
  - Metadata collection (time estimates, difficulty, prerequisites)
- **Comprehensive Crawling**: `TrailheadCrawler` can process individual modules, entire trails, or batch URLs
- **Progress Tracking**: Crawler maintains progress state and can resume interrupted crawls
- **Structured Data**: Uses dataclasses (`LessonContent`, `ModuleContent`, `ContentItem`) for type safety
- **Organized Selectors**: Element selectors are organized by purpose in dictionaries for maintainability
- **Browser runs in non-headless mode** by default for debugging
- **Session files** (`trailhead_session.json`, `token.json`) are gitignored
- **Gmail API** requires `credentials.json` file from Google Cloud Console
- **Environment variable** `SALESFORCE_EMAIL` required in `.env` file
- **reCAPTCHA handling** includes automatic detection and manual intervention prompts

## Security Considerations
- Never commit `credentials.json`, `.env`, `token.json`, or session files
- Gmail API uses read-only scope for security
- Session files contain authentication tokens and should be protected