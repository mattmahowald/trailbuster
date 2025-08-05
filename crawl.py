import json
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import dotenv

from salesforce.auth import LoginResult, SalesforceAuth
from salesforce.parse import LessonContent, ModuleContent, parse_lesson, parse_module
from trailbuster.logger import get_logger, log_crawler, log_performance, ProgressTracker


class TrailheadCrawler:
    """Crawls Trailhead modules and lessons to extract content for LLM processing."""

    def __init__(self, output_dir: str = "crawled_data"):
        self.output_dir = output_dir
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.logger = get_logger("CRAWLER")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Load existing progress if available
        self._load_progress()

    def crawl_module(
        self, module_url: str, auth: SalesforceAuth
    ) -> Optional[Dict[str, Any]]:
        """
        Crawl a single module and all its lessons.

        Args:
            module_url: URL of the module to crawl
            auth: Authenticated SalesforceAuth instance

        Returns:
            Dictionary containing module and lesson data
        """
        self.logger.start_operation("module_crawl", module_url=module_url)

        if module_url in self.visited_urls:
            self.logger.info(f"Skipping already visited: {module_url}")
            return self._load_existing_data(module_url)

        try:
            self.logger.info(f"Crawling module: {module_url}")

            # Navigate to module page
            page = auth.get_page()
            self._navigate_with_retry(page, module_url)

            # Parse module overview
            module_content = parse_module(page)
            self.logger.info(f"Found module: {module_content.title}")
            self.logger.info(f"Description: {module_content.description[:100]}...")
            self.logger.info(f"Found {len(module_content.lessons)} lessons")

            # Crawl each lesson
            lesson_data = []
            progress = ProgressTracker(len(module_content.lessons), "Crawling lessons")

            for i, lesson in enumerate(module_content.lessons, 1):
                lesson_title = lesson["title"]
                self.logger.info(
                    f"Crawling lesson {i}/{len(module_content.lessons)}: {lesson_title}"
                )

                try:
                    lesson_url = lesson["url"]
                    if lesson_url not in self.visited_urls:
                        self._navigate_with_retry(page, lesson_url)
                        lesson_content = parse_lesson(page)

                        lesson_dict = asdict(lesson_content)
                        lesson_data.append(lesson_dict)

                        self.logger.info(
                            f"Lesson completed: {lesson_title}",
                            {
                                "content_items": len(lesson_content.content),
                                "learning_objectives": len(
                                    lesson_content.learning_objectives
                                ),
                                "instructions": len(lesson_content.instructions),
                                "links": len(lesson_content.links),
                                "url": lesson_url,
                            },
                        )

                        self.visited_urls.add(lesson_url)
                        progress.update(1, f"Completed: {lesson_title}")

                        # Small delay between lessons
                        time.sleep(2)
                    else:
                        self.logger.info(f"Already visited: {lesson_title}")
                        existing_lesson = self._load_existing_lesson_data(lesson_url)
                        if existing_lesson:
                            lesson_data.append(existing_lesson)
                        progress.update(1, f"Skipped: {lesson_title}")

                except Exception as e:
                    self.logger.error(f"Failed to crawl lesson {lesson_title}: {e}")
                    self.failed_urls.add(lesson.get("url", ""))
                    progress.update(1, f"Failed: {lesson_title}")
                    continue

            # Compile final data
            crawl_result = {
                "module": asdict(module_content),
                "lessons": lesson_data,
                "crawl_timestamp": time.time(),
                "total_lessons": len(module_content.lessons),
                "successful_lessons": len(lesson_data),
                "failed_lessons": len(self.failed_urls),
            }

            # Save the data
            self._save_module_data(module_url, crawl_result)
            self.visited_urls.add(module_url)
            self._save_progress()

            self.logger.end_operation(
                "module_crawl", success=True, crawl_result=crawl_result
            )
            return crawl_result

        except Exception as e:
            self.logger.error(f"Failed to crawl module {module_url}: {e}")
            self.logger.end_operation("module_crawl", success=False, error=str(e))
            return None

    def crawl_trail(self, trail_url: str, auth: SalesforceAuth) -> Dict[str, Any]:
        """
        Crawl an entire trail and all its modules.

        Args:
            trail_url: URL of the trail to crawl
            auth: Authenticated SalesforceAuth instance

        Returns:
            Dictionary containing trail and module data
        """
        self.logger.start_operation("trail_crawl", trail_url=trail_url)

        if trail_url in self.visited_urls:
            self.logger.info(f"Skipping already visited trail: {trail_url}")
            return self._load_existing_data(trail_url)

        try:
            self.logger.info(f"Crawling trail: {trail_url}")

            # Navigate to trail page
            page = auth.get_page()
            self._navigate_with_retry(page, trail_url)

            # Extract trail information
            trail_info = self._extract_trail_info(page)
            self.logger.info(f"Found trail: {trail_info.get('title', 'N/A')}")

            # Get module URLs from trail
            module_elements = page.locator(
                "[data-testid='module-card'], .module-card, .trail-module"
            ).all()
            module_urls = []

            for element in module_elements:
                try:
                    link = element.locator("a[href]").first
                    href = link.get_attribute("href")
                    if href and "modules" in href:
                        if href.startswith("/"):
                            href = f"https://trailhead.salesforce.com{href}"
                        module_urls.append(href)
                except:
                    continue

            self.logger.info(f"Found {len(module_urls)} modules in trail")

            # Crawl each module
            module_data = []
            progress = ProgressTracker(len(module_urls), "Crawling trail modules")

            for i, module_url in enumerate(module_urls, 1):
                self.logger.info(
                    f"Crawling module {i}/{len(module_urls)}: {module_url}"
                )

                try:
                    module_result = self.crawl_module(module_url, auth)
                    if module_result:
                        module_data.append(module_result)
                        progress.update(1, f"Completed module {i}")
                    else:
                        progress.update(1, f"Failed module {i}")
                except Exception as e:
                    self.logger.error(f"Failed to crawl module {module_url}: {e}")
                    progress.update(1, f"Failed module {i}")
                    continue

            # Compile trail data
            trail_result = {
                "trail": trail_info,
                "modules": module_data,
                "crawl_timestamp": time.time(),
                "total_modules": len(module_urls),
                "successful_modules": len(module_data),
                "failed_modules": len(module_urls) - len(module_data),
            }

            # Save the data
            self._save_trail_data(trail_url, trail_result)
            self.visited_urls.add(trail_url)
            self._save_progress()

            self.logger.end_operation(
                "trail_crawl", success=True, trail_result=trail_result
            )
            return trail_result

        except Exception as e:
            self.logger.error(f"Failed to crawl trail {trail_url}: {e}")
            self.logger.end_operation("trail_crawl", success=False, error=str(e))
            return {"error": str(e)}

    def crawl_urls_from_file(
        self, urls_file: str, auth: SalesforceAuth
    ) -> Dict[str, Any]:
        """
        Crawl URLs from a file.

        Args:
            urls_file: Path to file containing URLs
            auth: Authenticated SalesforceAuth instance

        Returns:
            Dictionary containing crawl results
        """
        self.logger.start_operation("batch_crawl", urls_file=urls_file)

        try:
            with open(urls_file, "r") as f:
                urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

            self.logger.info(f"Loaded {len(urls)} URLs from {urls_file}")

            results = {}
            progress = ProgressTracker(len(urls), "Batch crawling URLs")

            for i, url in enumerate(urls, 1):
                self.logger.info(f"Processing URL {i}/{len(urls)}: {url}")

                try:
                    if "trails" in url:
                        result = self.crawl_trail(url, auth)
                    else:
                        result = self.crawl_module(url, auth)

                    results[url] = result
                    progress.update(1, f"Completed URL {i}")

                except Exception as e:
                    self.logger.error(f"Failed to crawl URL {url}: {e}")
                    results[url] = {"error": str(e)}
                    progress.update(1, f"Failed URL {i}")

            # Save batch results
            self._save_batch_results(results)

            self.logger.end_operation("batch_crawl", success=True, results=results)
            return results

        except Exception as e:
            self.logger.error(f"Failed to process URLs file {urls_file}: {e}")
            self.logger.end_operation("batch_crawl", success=False, error=str(e))
            return {"error": str(e)}

    def _navigate_with_retry(self, page, url: str, max_retries: int = 3) -> None:
        """Navigate to URL with retry logic."""
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"Navigation attempt {attempt + 1}/{max_retries} to {url}"
                )
                page.goto(url, wait_until="networkidle", timeout=30000)
                break
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    self.logger.debug(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise e

        duration = time.time() - start_time
        log_performance("page_navigation", duration, url=url, attempts=attempt + 1)

    def _extract_trail_info(self, page) -> Dict[str, Any]:
        """Extract trail information from the page."""
        try:
            # Extract title
            title_selectors = [
                "[data-testid='trail-title']",
                ".trail-title",
                "h1",
                ".trail-header h1",
            ]

            title = "Unknown Trail"
            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        title = element.text_content().strip()
                        break
                except:
                    continue

            # Extract description
            description_selectors = [
                "[data-testid='trail-description']",
                ".trail-description",
                ".trail-intro",
                "p:first-of-type",
            ]

            description = "No description available"
            for selector in description_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        description = element.text_content().strip()
                        break
                except:
                    continue

            return {
                "title": title,
                "description": description,
                "url": page.url,
            }

        except Exception as e:
            self.logger.error(f"Error extracting trail info: {e}")
            return {
                "title": "Unknown Trail",
                "description": "Error extracting description",
                "url": page.url,
            }

    def _save_module_data(self, module_url: str, data: Dict[str, Any]) -> None:
        """Save module data to file."""
        try:
            filename = f"module_{hash(module_url)}.json"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(f"Saved module data to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving module data: {e}")

    def _save_trail_data(self, trail_url: str, data: Dict[str, Any]) -> None:
        """Save trail data to file."""
        try:
            filename = f"trail_{hash(trail_url)}.json"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            self.logger.debug(f"Saved trail data to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving trail data: {e}")

    def _save_batch_results(self, results: Dict[str, Any]) -> None:
        """Save batch crawl results to file."""
        try:
            timestamp = int(time.time())
            filename = f"batch_results_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, "w") as f:
                json.dump(results, f, indent=2)

            self.logger.debug(f"Saved batch results to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving batch results: {e}")

    def _save_progress(self) -> None:
        """Save progress to file."""
        try:
            progress_data = {
                "visited_urls": list(self.visited_urls),
                "failed_urls": list(self.failed_urls),
                "timestamp": time.time(),
            }

            progress_file = os.path.join(self.output_dir, "progress.json")
            with open(progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

            self.logger.debug(f"Saved progress to {progress_file}")
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")

    def _load_progress(self) -> None:
        """Load progress from file."""
        try:
            progress_file = os.path.join(self.output_dir, "progress.json")
            if os.path.exists(progress_file):
                with open(progress_file, "r") as f:
                    progress_data = json.load(f)

                self.visited_urls = set(progress_data.get("visited_urls", []))
                self.failed_urls = set(progress_data.get("failed_urls", []))

                self.logger.info(
                    f"Loaded progress: {len(self.visited_urls)} visited URLs, {len(self.failed_urls)} failed URLs"
                )
        except Exception as e:
            self.logger.warning(f"Error loading progress: {e}")

    def _load_existing_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Load existing data for a URL."""
        try:
            filename = (
                f"module_{hash(url)}.json"
                if "modules" in url
                else f"trail_{hash(url)}.json"
            )
            filepath = os.path.join(self.output_dir, filename)

            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading existing data: {e}")

        return None

    def _load_existing_lesson_data(self, lesson_url: str) -> Optional[Dict[str, Any]]:
        """Load existing lesson data."""
        try:
            # Look for lesson data in module files
            for filename in os.listdir(self.output_dir):
                if filename.startswith("module_") and filename.endswith(".json"):
                    filepath = os.path.join(self.output_dir, filename)
                    with open(filepath, "r") as f:
                        data = json.load(f)

                    lessons = data.get("lessons", [])
                    for lesson in lessons:
                        if lesson.get("url") == lesson_url:
                            return lesson
        except Exception as e:
            self.logger.error(f"Error loading existing lesson data: {e}")

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get crawling statistics."""
        total_urls = len(self.visited_urls) + len(self.failed_urls)
        success_rate = (
            (len(self.visited_urls) / total_urls * 100) if total_urls > 0 else 0
        )

        stats = {
            "visited_urls": len(self.visited_urls),
            "failed_urls": len(self.failed_urls),
            "total_urls": total_urls,
            "success_rate": success_rate,
            "output_directory": self.output_dir,
        }

        self.logger.info("Crawling statistics", stats)
        return stats


def main():
    """Test the crawler."""
    dotenv.load_dotenv()
    email = os.getenv("SALESFORCE_EMAIL")

    if not email:
        print("SALESFORCE_EMAIL not found in environment variables")
        sys.exit(1)

    crawler = TrailheadCrawler()

    with SalesforceAuth() as auth:
        result = auth.login(email)
        if result.is_logged_in:
            module_url = "https://trailhead.salesforce.com/content/learn/modules/starting_force_com"
            data = crawler.crawl_module(module_url, auth)
            if data:
                print("Crawl completed successfully!")
            else:
                print("Crawl failed!")
        else:
            print(f"Login failed: {result.error}")


if __name__ == "__main__":
    main()
