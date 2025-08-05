#!/usr/bin/env python3
"""
TrailBuster - Salesforce Trailhead Automation Tool

Main entry point for crawling Trailhead modules, lessons, and trails.
"""

import os
import sys
from typing import Optional

import dotenv

from salesforce.auth import SalesforceAuth
from salesforce.crawl import TrailheadCrawler
from trailbuster.logger import get_logger, log_main, setup_logging

# Default module URL for testing
DEFAULT_MODULE_URL = (
    "https://trailhead.salesforce.com/content/learn/modules/starting_force_com"
)

# Setup logging
logger = get_logger("MAIN")


def print_crawl_summary(crawl_data: dict) -> None:
    """Print a summary of the crawled data."""
    module = crawl_data.get("module", {})
    lessons = crawl_data.get("lessons", [])

    log_main("Module crawl completed!")
    log_main(f"Module: {module.get('title', 'N/A')}")
    log_main(f"Description: {module.get('description', 'N/A')[:100]}...")
    log_main(f"Lessons crawled: {len(lessons)}")

    if lessons:
        log_main("Lesson details:")
        for i, lesson in enumerate(lessons, 1):
            log_main(f"  {i}. {lesson.get('title', 'N/A')}")
            logger.info(
                "Lesson details",
                {
                    "content_items": len(lesson.get("content", [])),
                    "learning_objectives": len(lesson.get("learning_objectives", [])),
                    "instructions": len(lesson.get("instructions", [])),
                },
            )


def handle_module_crawl(
    email: str, module_url: str = DEFAULT_MODULE_URL, use_saved_session: bool = True
) -> None:
    """Handle login process and crawl the specified module."""
    logger.start_operation(
        "module_crawl", module_url=module_url, use_saved_session=use_saved_session
    )

    crawler = TrailheadCrawler()

    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)

            if result.session_restored:
                log_main("Session restored! Starting module crawl...")
            elif result.is_logged_in:
                log_main("Login completed! Starting module crawl...")
            else:
                logger.error(f"Login failed: {result.error}")
                logger.end_operation("module_crawl", success=False, error=result.error)
                return

            # Use the page from the login result
            auth.page = result.page

            # Crawl the specified module
            log_main("Starting comprehensive crawl of module...")
            crawl_data = crawler.crawl_module(module_url, auth)

            if crawl_data:
                print_crawl_summary(crawl_data)

                # Show crawling statistics
                stats = crawler.get_stats()
                log_main("Crawl Statistics")
                logger.info("Statistics", stats)
                logger.end_operation("module_crawl", success=True, stats=stats)
            else:
                logger.error("Failed to crawl module")
                logger.end_operation("module_crawl", success=False)

        except Exception as e:
            logger.error(f"Error during module crawl: {e}")
            logger.end_operation("module_crawl", success=False, error=str(e))


def handle_trail_crawl(
    email: str, trail_url: str, use_saved_session: bool = True
) -> None:
    """Handle login process and crawl the specified trail."""
    logger.start_operation(
        "trail_crawl", trail_url=trail_url, use_saved_session=use_saved_session
    )

    crawler = TrailheadCrawler()

    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)

            if result.session_restored:
                log_main("Session restored! Starting trail crawl...")
            elif result.is_logged_in:
                log_main("Login completed! Starting trail crawl...")
            else:
                logger.error(f"Login failed: {result.error}")
                logger.end_operation("trail_crawl", success=False, error=result.error)
                return

            # Use the page from the login result
            auth.page = result.page

            # Crawl the trail
            log_main("Starting comprehensive crawl of trail...")
            trail_data = crawler.crawl_trail(trail_url, auth)

            if "error" not in trail_data:
                log_main("Trail crawl completed!")
                trail_info = trail_data.get("trail", {})
                modules = trail_data.get("modules", [])

                log_main(f"Trail: {trail_info.get('title', 'N/A')}")
                log_main(f"Modules processed: {len(modules)}")

                # Show statistics
                stats = crawler.get_stats()
                log_main("Crawl Statistics")
                logger.info("Statistics", stats)
                logger.end_operation("trail_crawl", success=True, stats=stats)
            else:
                logger.error(f"Trail crawl failed: {trail_data['error']}")
                logger.end_operation(
                    "trail_crawl", success=False, error=trail_data["error"]
                )

        except Exception as e:
            logger.error(f"Error during trail crawl: {e}")
            logger.end_operation("trail_crawl", success=False, error=str(e))


def handle_batch_crawl(
    email: str, urls_file: str, use_saved_session: bool = True
) -> None:
    """Handle login process and crawl URLs from a file."""
    logger.start_operation(
        "batch_crawl", urls_file=urls_file, use_saved_session=use_saved_session
    )

    if not os.path.exists(urls_file):
        logger.error(f"URLs file not found: {urls_file}")
        logger.end_operation("batch_crawl", success=False, error="File not found")
        return

    crawler = TrailheadCrawler()

    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)

            if result.session_restored:
                log_main("Session restored! Starting batch crawl...")
            elif result.is_logged_in:
                log_main("Login completed! Starting batch crawl...")
            else:
                logger.error(f"Login failed: {result.error}")
                logger.end_operation("batch_crawl", success=False, error=result.error)
                return

            # Use the page from the login result
            auth.page = result.page

            # Crawl URLs from file
            log_main(f"Starting batch crawl from {urls_file}...")
            batch_results = crawler.crawl_urls_from_file(urls_file, auth)

            if "error" not in batch_results:
                log_main("Batch crawl completed!")
                log_main(f"URLs processed: {len(batch_results)}")

                # Show statistics
                stats = crawler.get_stats()
                log_main("Final Statistics")
                logger.info("Statistics", stats)
                logger.end_operation("batch_crawl", success=True, stats=stats)
            else:
                logger.error(f"Batch crawl failed: {batch_results['error']}")
                logger.end_operation(
                    "batch_crawl", success=False, error=batch_results["error"]
                )

        except Exception as e:
            logger.error(f"Error during batch crawl: {e}")
            logger.end_operation("batch_crawl", success=False, error=str(e))


def show_crawler_stats() -> None:
    """Show crawling statistics."""
    crawler = TrailheadCrawler()
    stats = crawler.get_stats()

    log_main("Crawling Statistics")
    logger.info("Statistics", stats)


def clear_session() -> None:
    """Clear saved session."""
    try:
        auth = SalesforceAuth()
        auth.clear_session()
        log_main("Session cleared successfully!")
    except Exception as e:
        logger.error(f"Error clearing session: {e}")


def print_help():
    """Print help information."""
    help_text = """
TrailBuster - Salesforce Trailhead Automation Tool

Usage:
  python main.py                                    # Crawl default module
  python main.py <module_url>                       # Crawl specific module
  python main.py trail <trail_url>                  # Crawl entire trail
  python main.py batch <urls_file>                  # Batch crawl from file
  python main.py stats                              # Show crawling statistics
  python main.py --clear-session                    # Clear saved session
  python main.py --no-session                       # Force new login
  python main.py --help                             # Show this help

Examples:
  python main.py https://trailhead.salesforce.com/content/learn/modules/starting_force_com
  python main.py trail https://trailhead.salesforce.com/trails/force_com_admin_beginner
  python main.py batch sample_urls.txt

Options:
  --no-session    Force new login (don't use saved session)
  --clear-session Clear saved session data
  --help          Show this help message
"""
    print(help_text)


def main():
    """Main entry point for TrailBuster."""
    # Setup logging first
    setup_logging(log_level="INFO")

    logger.start_operation("trailbuster_application")

    dotenv.load_dotenv()
    email = os.getenv("SALESFORCE_EMAIL")

    if not email:
        logger.critical("SALESFORCE_EMAIL not found in environment variables")
        logger.critical(
            "Please add SALESFORCE_EMAIL=your_email@example.com to your .env file"
        )
        sys.exit(1)

    # Parse command line arguments
    if len(sys.argv) == 1:
        # Default behavior: crawl default module
        log_main("No URL specified, crawling default module...")
        handle_module_crawl(email)
        logger.end_operation("trailbuster_application", success=True)
        return

    command = sys.argv[1]

    # Help command
    if command in ["--help", "-h", "help"]:
        print_help()
        logger.end_operation("trailbuster_application", success=True)
        return

    # Session management commands
    if command == "--clear-session":
        clear_session()
        logger.end_operation("trailbuster_application", success=True)
        return

    # Statistics command
    elif command == "stats":
        show_crawler_stats()
        logger.end_operation("trailbuster_application", success=True)
        return

    # Trail crawling command
    elif command == "trail":
        if len(sys.argv) < 3:
            logger.error("Trail URL required for trail command")
            logger.error("Usage: python main.py trail <trail_url>")
            sys.exit(1)

        trail_url = sys.argv[2]
        use_saved_session = "--no-session" not in sys.argv
        handle_trail_crawl(email, trail_url, use_saved_session)
        logger.end_operation("trailbuster_application", success=True)
        return

    # Batch crawling command
    elif command == "batch":
        if len(sys.argv) < 3:
            logger.error("URLs file required for batch command")
            logger.error("Usage: python main.py batch <urls_file>")
            sys.exit(1)

        urls_file = sys.argv[2]
        use_saved_session = "--no-session" not in sys.argv
        handle_batch_crawl(email, urls_file, use_saved_session)
        logger.end_operation("trailbuster_application", success=True)
        return

    # Check for --no-session flag
    use_saved_session = "--no-session" not in sys.argv

    # If first argument looks like a URL, treat it as a module URL
    if command.startswith("http"):
        module_url = command
        handle_module_crawl(email, module_url, use_saved_session)
        logger.end_operation("trailbuster_application", success=True)
        return

    # If we get here, the command wasn't recognized
    logger.error(f"Unknown command: {command}")
    logger.error("Use --help for usage information")
    logger.end_operation(
        "trailbuster_application", success=False, error=f"Unknown command: {command}"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
