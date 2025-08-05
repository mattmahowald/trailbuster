# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrailBuster is a Python automation tool for Salesforce Trailhead that uses Playwright for browser automation and Gmail API for verification code retrieval. The project automates login to Salesforce Trailhead, handles two-factor authentication, and can read module content with comprehensive logging and beautiful progress tracking.

## Development Commands

### Installation and Setup

```bash
# Complete development setup (recommended)
make setup

# Install dependencies with Poetry
make install-dev

# Install Playwright browsers
make install-playwright

# Create environment template
make env-create
```

### Running the Application

```bash
# Module Crawling
make run                                    # Crawl default module
make run-module URL=<module_url>            # Crawl specific module
make run-trail URL=<trail_url>              # Crawl entire trail
make run-batch FILE=<urls_file>             # Batch crawl from file

# Options
make run-stats                              # Show crawling statistics
make run-clear                              # Clear saved session
make run-no-session                         # Force new login
make run-help                               # Show detailed help

# Examples
make example-module                         # Run example module crawl
make example-trail                          # Run example trail crawl
make example-batch                          # Run example batch crawl
```

### Code Quality and Development

```bash
# Formatting and Linting
make format                                 # Format code with black and isort
make format-check                           # Check formatting without changes
make lint                                   # Run all linting checks (flake8, mypy, ruff)
make check                                  # Run all quality checks (format + lint + test)

# Testing
make test                                   # Run all tests
make test-unit                              # Run unit tests only
make test-integration                       # Run integration tests only
make test-cov                               # Run tests with coverage report

# Development Workflow
make dev                                    # Quick development cycle (format, lint, test)
make dev-setup                              # Complete development environment setup
make pre-commit                             # Run all checks for pre-commit

# Poetry Management
make poetry-add PKG=<package_name>          # Add a dependency
make poetry-add-dev PKG=<package_name>      # Add a development dependency
make poetry-update                          # Update all dependencies
make poetry-show                            # Show dependency tree
```

### Utilities

```bash
# Cleanup and Maintenance
make clean                                  # Clean up generated files and caches
make security-check                         # Check for sensitive files in git

# Documentation and Profiling
make docs                                   # Generate documentation
make profile                                # Run performance profiling

# Shell Access
make shell                                  # Open Poetry shell
```

## Architecture

### Core Components

- **Main Application** (`main.py`): Streamlined entry point with comprehensive logging and progress tracking
- **SalesforceAuth** (`salesforce/auth.py`): Main authentication class with detailed logging and session management
- **TrailheadCrawler** (`crawl.py`): Comprehensive crawler with progress bars and performance monitoring
- **Content Parsers** (`salesforce/parse.py`): Structured parsing functions with detailed link extraction logging
- **Gmail Integration** (`salesforce/auth_code.py`): Clean Gmail API wrapper with verification code retrieval logging
- **Logging System** (`trailbuster/logger.py`): Beautiful, structured logging with colors, emojis, and JSON output

### Key Design Patterns

- **Comprehensive Logging**: Beautiful colored console output with component-specific styling and structured JSON logging
- **Progress Tracking**: Real-time progress bars with ETA calculations for all crawling operations
- **Performance Monitoring**: Automatic timing and performance metrics for all operations
- **Component-Based Architecture**: Each component (AUTH, CRAWLER, PARSER, GMAIL) has its own logging and error handling
- **Session Persistence**: Browser sessions are saved to `trailhead_session.json` to avoid repeated logins
- **Retry Logic**: Built-in retry mechanisms for network operations and element finding
- **Poetry Integration**: Full dependency management with Poetry for consistent environments

### Authentication Flow

1. Check for existing valid session with detailed logging
2. Navigate to Trailhead login page with performance tracking
3. Enter email address with element detection logging
4. Handle reCAPTCHA if present (manual intervention with user prompts)
5. Retrieve verification code from Gmail with detailed API logging
6. Submit verification code with success/failure tracking
7. Save session for future use with file operation logging

### File Structure

```
├── main.py                    # Unified entry point with comprehensive logging
├── crawl.py                   # TrailheadCrawler with progress tracking and performance monitoring
├── Makefile                   # Comprehensive development utilities with Poetry integration
├── pyproject.toml            # Poetry configuration with all dependencies and tool configs
├── .flake8                   # Flake8 linting configuration
├── .pre-commit-config.yaml   # Pre-commit hooks for automated quality checks
├── sample_urls.txt           # Example URLs for batch crawling
├── trailbuster/
│   ├── __init__.py          # Package initialization
│   └── logger.py            # Comprehensive logging system with colors and JSON output
├── salesforce/
│   ├── auth.py              # SalesforceAuth with detailed logging and session management
│   ├── auth_code.py         # Gmail API integration with verification code logging
│   └── parse.py             # Content parsing with link extraction debugging
├── tests/                   # Comprehensive test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data and fixtures
├── logs/                   # Rotating log files (JSON format)
├── crawled_data/           # Structured output data
└── README.md              # Comprehensive setup and usage documentation
```

### Logging System Features

**Beautiful Console Output:**

- Colored output with component-specific emojis and colors
- Precise timestamps with millisecond precision
- Structured format: `12:50:31.685 ℹ️ 🚀 MAIN INFO     Starting trailbuster_application`

**Component-Specific Logging:**

- 🔐 **AUTH** (Magenta) - Authentication and session management
- 🕷️ **CRAWLER** (Blue) - Web crawling operations with progress bars
- 📄 **PARSER** (Cyan) - Content parsing and link extraction debugging
- 📧 **GMAIL** (Green) - Gmail API operations and verification code retrieval
- 🚀 **MAIN** (White) - Main application flow and coordination
- 🔗 **LINK** (Yellow) - Link extraction debugging and statistics
- 📊 **PROGRESS** (Blue) - Progress tracking and ETA calculations
- ⚡ **PERFORMANCE** (Magenta) - Performance metrics and timing

**Advanced Features:**

- JSON logging for file output with structured data
- Rotating log files (10MB max, keep 5 files)
- Progress bars with real-time ETA calculations
- Performance monitoring for all operations
- Link extraction debugging with detailed statistics
- Operation start/end tracking with success/failure metrics

### Important Implementation Details

- **Streamlined Interface**: `main.py` provides a clean, focused entry point with comprehensive logging
- **LLM-Optimized Content**: All extracted content is structured specifically for LLM processing with:
  - Learning objectives and instructions
  - Content categorization (text, code, lists, headings)
  - Link extraction and validation with detailed logging
  - Metadata collection (time estimates, difficulty, prerequisites)
- **Comprehensive Crawling**: `TrailheadCrawler` can process individual modules, entire trails, or batch URLs with progress tracking
- **Progress Tracking**: Beautiful progress bars with ETA calculations for all operations
- **Structured Data**: Uses dataclasses (`LessonContent`, `ModuleContent`, `ContentItem`) for type safety
- **Organized Selectors**: Element selectors are organized by purpose in dictionaries for maintainability
- **Browser runs in non-headless mode** by default for debugging
- **Session files** (`trailhead_session.json`, `token.json`) are gitignored
- **Gmail API** requires `credentials.json` file from Google Cloud Console
- **Environment variable** `SALESFORCE_EMAIL` required in `.env` file
- **reCAPTCHA handling** includes automatic detection and manual intervention prompts
- **Poetry Integration**: Full dependency management with development and production dependencies

## Development Workflow

### Quick Start

```bash
# 1. Setup development environment
make setup

# 2. Create environment file
make env-create
# Edit .env with your SALESFORCE_EMAIL

# 3. Run a test crawl
make example-module

# 4. Check logs
ls logs/  # View JSON log files
```

### Code Quality Workflow

```bash
# Before committing
make dev  # Runs format, lint, and test

# Or run individually
make format
make lint
make test
```

### Adding Dependencies

```bash
# Add production dependency
make poetry-add PKG=requests

# Add development dependency
make poetry-add-dev PKG=pytest-mock
```

## Security Considerations

- Never commit `credentials.json`, `.env`, `token.json`, or session files
- Gmail API uses read-only scope for security
- Session files contain authentication tokens and should be protected
- Log files may contain sensitive information and should be reviewed before sharing
- Use `make security-check` to verify no sensitive files are in git

## Troubleshooting

### Common Issues

1. **Colorama not found**: Run `poetry run pip install colorama` or `make install-dev`
2. **Gmail API errors**: Ensure `credentials.json` is in project root
3. **Session issues**: Use `make run-clear` to clear saved sessions
4. **Link extraction problems**: Check logs for detailed debugging information
5. **Performance issues**: Use `make profile` for performance analysis

### Debugging

- All operations are logged with detailed information
- Check `logs/` directory for JSON log files
- Use `make run-stats` to see crawling statistics
- Link extraction issues are logged with detailed statistics
- Performance metrics are automatically logged for all operations

## Performance Monitoring

- Automatic performance tracking for all operations
- Navigation timing with retry statistics
- Link extraction performance metrics
- Gmail API response times
- Overall crawl performance statistics
- Use `make profile` for detailed performance analysis
