import json
import os
import sys
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin, urlparse
import dotenv
from dataclasses import asdict

from salesforce.auth import SalesforceAuth, LoginResult
from salesforce.parse import parse_lesson, parse_module, LessonContent, ModuleContent


class TrailheadCrawler:
    """Crawls Trailhead modules and lessons to extract content for LLM processing."""
    
    def __init__(self, output_dir: str = "crawled_data"):
        self.output_dir = output_dir
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Load existing progress if available
        self._load_progress()
    
    def crawl_module(self, module_url: str, auth: SalesforceAuth) -> Optional[Dict[str, Any]]:
        """
        Crawl a single module and all its lessons.
        
        Args:
            module_url: URL of the module to crawl
            auth: Authenticated SalesforceAuth instance
            
        Returns:
            Dictionary containing module and lesson data
        """
        if module_url in self.visited_urls:
            print(f"⏭️  Skipping already visited: {module_url}")
            return self._load_existing_data(module_url)
        
        try:
            print(f"🔍 Crawling module: {module_url}")
            
            # Navigate to module page
            page = auth.get_page()
            self._navigate_with_retry(page, module_url)
            
            # Parse module overview
            module_content = parse_module(page)
            print(f"📚 Found module: {module_content.title}")
            print(f"📄 Description: {module_content.description[:100]}...")
            print(f"📝 Found {len(module_content.lessons)} lessons")
            
            # Crawl each lesson
            lesson_data = []
            for i, lesson in enumerate(module_content.lessons, 1):
                print(f"\n📖 Crawling lesson {i}/{len(module_content.lessons)}: {lesson['title']}")
                
                try:
                    lesson_url = lesson['url']
                    if lesson_url not in self.visited_urls:
                        self._navigate_with_retry(page, lesson_url)
                        lesson_content = parse_lesson(page)
                        
                        lesson_dict = asdict(lesson_content)
                        lesson_data.append(lesson_dict)
                        
                        print(f"  ✅ Content items: {len(lesson_content.content)}")
                        print(f"  ✅ Learning objectives: {len(lesson_content.learning_objectives)}")
                        print(f"  ✅ Instructions: {len(lesson_content.instructions)}")
                        print(f"  ✅ Links: {len(lesson_content.links)}")
                        
                        self.visited_urls.add(lesson_url)
                        
                        # Small delay between lessons
                        time.sleep(2)
                    else:
                        print(f"  ⏭️  Already visited: {lesson['title']}")
                        existing_lesson = self._load_existing_lesson_data(lesson_url)
                        if existing_lesson:
                            lesson_data.append(existing_lesson)
                            
                except Exception as e:
                    print(f"  ❌ Failed to crawl lesson {lesson['title']}: {e}")
                    self.failed_urls.add(lesson.get('url', ''))
                    continue
            
            # Compile final data
            crawl_result = {
                'module': asdict(module_content),
                'lessons': lesson_data,
                'crawl_timestamp': time.time(),
                'crawl_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Save data
            self._save_module_data(module_url, crawl_result)
            self.visited_urls.add(module_url)
            self._save_progress()
            
            print(f"✅ Module crawl complete: {len(lesson_data)} lessons processed")
            return crawl_result
            
        except Exception as e:
            print(f"❌ Failed to crawl module {module_url}: {e}")
            self.failed_urls.add(module_url)
            return None
    
    def crawl_trail(self, trail_url: str, auth: SalesforceAuth) -> Dict[str, Any]:
        """
        Crawl an entire trail (collection of modules).
        
        Args:
            trail_url: URL of the trail to crawl
            auth: Authenticated SalesforceAuth instance
            
        Returns:
            Dictionary containing trail and all module data
        """
        try:
            print(f"🛤️  Crawling trail: {trail_url}")
            
            page = auth.get_page()
            self._navigate_with_retry(page, trail_url)
            
            # Extract trail information and module links
            trail_info = self._extract_trail_info(page)
            print(f"🛤️  Trail: {trail_info['title']}")
            print(f"📚 Found {len(trail_info['modules'])} modules")
            
            # Crawl each module in the trail
            modules_data = []
            for i, module in enumerate(trail_info['modules'], 1):
                print(f"\n📚 Processing module {i}/{len(trail_info['modules'])}: {module['title']}")
                
                module_data = self.crawl_module(module['url'], auth)
                if module_data:
                    modules_data.append(module_data)
                
                # Longer delay between modules
                time.sleep(5)
            
            # Compile trail data
            trail_result = {
                'trail': trail_info,
                'modules': modules_data,
                'crawl_timestamp': time.time(),
                'crawl_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Save trail data
            self._save_trail_data(trail_url, trail_result)
            
            print(f"🎉 Trail crawl complete: {len(modules_data)} modules processed")
            return trail_result
            
        except Exception as e:
            print(f"❌ Failed to crawl trail {trail_url}: {e}")
            return {'error': str(e)}
    
    def crawl_urls_from_file(self, urls_file: str, auth: SalesforceAuth) -> Dict[str, Any]:
        """
        Crawl multiple URLs from a file.
        
        Args:
            urls_file: Path to file containing URLs (one per line)
            auth: Authenticated SalesforceAuth instance
            
        Returns:
            Dictionary containing results for all URLs
        """
        try:
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            print(f"📋 Found {len(urls)} URLs to crawl")
            
            results = {}
            for i, url in enumerate(urls, 1):
                print(f"\n📊 Processing URL {i}/{len(urls)}: {url}")
                
                if 'trails' in url:
                    result = self.crawl_trail(url, auth)
                    results[url] = result
                elif 'modules' in url:
                    result = self.crawl_module(url, auth)
                    results[url] = result
                else:
                    print(f"⚠️  Unknown URL type, treating as module: {url}")
                    result = self.crawl_module(url, auth)
                    results[url] = result
                
                # Delay between different URLs
                time.sleep(10)
            
            # Save consolidated results
            self._save_batch_results(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Failed to process URLs file: {e}")
            return {'error': str(e)}
    
    def _navigate_with_retry(self, page, url: str, max_retries: int = 3) -> None:
        """Navigate to URL with retry logic."""
        for attempt in range(max_retries):
            try:
                print(f"🔗 Navigating to: {url} (attempt {attempt + 1})")
                page.goto(url, timeout=60000)
                
                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                time.sleep(3)  # Wait for dynamic content
                return
                
            except Exception as e:
                print(f"❌ Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⏰ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def _extract_trail_info(self, page) -> Dict[str, Any]:
        """Extract trail information and module links."""
        # Extract trail title
        title_selectors = [
            "h1",
            "[data-testid='trail-title']",
            ".trail-title"
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
        desc_selectors = [
            "[data-testid='trail-description']",
            ".trail-description",
            ".description",
            "p:first-of-type"
        ]
        
        description = ""
        for selector in desc_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible():
                    description = element.text_content().strip()
                    if len(description) > 20:
                        break
            except:
                continue
        
        # Extract module links
        module_selectors = [
            ".trail-modules a",
            ".modules-list a",
            ".module-list a",
            "[data-testid='module-link']"
        ]
        
        modules = []
        for selector in module_selectors:
            try:
                elements = page.locator(selector).all()
                if elements:
                    for elem in elements:
                        href = elem.get_attribute("href")
                        text = elem.text_content().strip()
                        
                        if href and text and 'modules' in href:
                            if href.startswith('/'):
                                href = f"https://trailhead.salesforce.com{href}"
                            
                            modules.append({
                                'title': text,
                                'url': href
                            })
                    
                    if modules:
                        break
            except:
                continue
        
        return {
            'title': title,
            'description': description,
            'url': page.url,
            'modules': modules
        }
    
    def _save_module_data(self, module_url: str, data: Dict[str, Any]) -> None:
        """Save module data to file."""
        # Create filename from URL
        parsed_url = urlparse(module_url)
        filename = parsed_url.path.replace('/', '_').replace('-', '_') + '.json'
        filepath = os.path.join(self.output_dir, 'modules', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved module data: {filepath}")
    
    def _save_trail_data(self, trail_url: str, data: Dict[str, Any]) -> None:
        """Save trail data to file."""
        # Create filename from URL
        parsed_url = urlparse(trail_url)
        filename = parsed_url.path.replace('/', '_').replace('-', '_') + '.json'
        filepath = os.path.join(self.output_dir, 'trails', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved trail data: {filepath}")
    
    def _save_batch_results(self, results: Dict[str, Any]) -> None:
        """Save batch processing results."""
        timestamp = int(time.time())
        filename = f"batch_results_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved batch results: {filepath}")
    
    def _save_progress(self) -> None:
        """Save crawling progress."""
        progress = {
            'visited_urls': list(self.visited_urls),
            'failed_urls': list(self.failed_urls),
            'last_updated': time.time()
        }
        
        filepath = os.path.join(self.output_dir, 'progress.json')
        with open(filepath, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def _load_progress(self) -> None:
        """Load existing crawling progress."""
        filepath = os.path.join(self.output_dir, 'progress.json')
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    progress = json.load(f)
                
                self.visited_urls = set(progress.get('visited_urls', []))
                self.failed_urls = set(progress.get('failed_urls', []))
                
                print(f"📊 Loaded progress: {len(self.visited_urls)} visited, {len(self.failed_urls)} failed")
            except Exception as e:
                print(f"⚠️  Failed to load progress: {e}")
    
    def _load_existing_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Load existing data for a URL."""
        parsed_url = urlparse(url)
        filename = parsed_url.path.replace('/', '_').replace('-', '_') + '.json'
        
        # Try modules directory first
        filepath = os.path.join(self.output_dir, 'modules', filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Try trails directory
        filepath = os.path.join(self.output_dir, 'trails', filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return None
    
    def _load_existing_lesson_data(self, lesson_url: str) -> Optional[Dict[str, Any]]:
        """Load existing lesson data from module files."""
        # This is a simplified approach - in practice, you might want to index lessons separately
        for root, dirs, files in os.walk(os.path.join(self.output_dir, 'modules')):
            for file in files:
                if file.endswith('.json'):
                    try:
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        # Check if this module contains the lesson
                        for lesson in data.get('lessons', []):
                            if lesson.get('url') == lesson_url:
                                return lesson
                    except:
                        continue
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get crawling statistics."""
        return {
            'visited_urls': len(self.visited_urls),
            'failed_urls': len(self.failed_urls),
            'success_rate': len(self.visited_urls) / (len(self.visited_urls) + len(self.failed_urls)) * 100 if (len(self.visited_urls) + len(self.failed_urls)) > 0 else 0,
            'output_directory': self.output_dir
        }


def main():
    """Main entry point for the crawler."""
    dotenv.load_dotenv()
    email = os.getenv("SALESFORCE_EMAIL")
    
    if not email:
        print("❌ SALESFORCE_EMAIL not found in environment variables")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python crawl.py <command> [args]")
        print("Commands:")
        print("  module <url>        - Crawl a single module")
        print("  trail <url>         - Crawl an entire trail")
        print("  batch <urls_file>   - Crawl URLs from file")
        print("  stats               - Show crawling statistics")
        sys.exit(1)
    
    command = sys.argv[1]
    crawler = TrailheadCrawler()
    
    if command == "stats":
        stats = crawler.get_stats()
        print(f"📊 Crawling Statistics:")
        print(f"  Visited URLs: {stats['visited_urls']}")
        print(f"  Failed URLs: {stats['failed_urls']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"  Output Directory: {stats['output_directory']}")
        return
    
    # Commands that require authentication
    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session=True)
            
            if not result.is_logged_in:
                print(f"❌ Login failed: {result.error}")
                sys.exit(1)
            
            if result.session_restored:
                print("🎉 Session restored successfully")
            else:
                print("🎉 Login completed successfully")
            
            # Execute commands
            if command == "module":
                if len(sys.argv) < 3:
                    print("❌ Module URL required")
                    sys.exit(1)
                
                module_url = sys.argv[2]
                result = crawler.crawl_module(module_url, auth)
                if result:
                    print(f"✅ Module crawl completed successfully")
                else:
                    print(f"❌ Module crawl failed")
            
            elif command == "trail":
                if len(sys.argv) < 3:
                    print("❌ Trail URL required")
                    sys.exit(1)
                
                trail_url = sys.argv[2]
                result = crawler.crawl_trail(trail_url, auth)
                if 'error' not in result:
                    print(f"✅ Trail crawl completed successfully")
                else:
                    print(f"❌ Trail crawl failed: {result['error']}")
            
            elif command == "batch":
                if len(sys.argv) < 3:
                    print("❌ URLs file required")
                    sys.exit(1)
                
                urls_file = sys.argv[2]
                if not os.path.exists(urls_file):
                    print(f"❌ URLs file not found: {urls_file}")
                    sys.exit(1)
                
                result = crawler.crawl_urls_from_file(urls_file, auth)
                if 'error' not in result:
                    print(f"✅ Batch crawl completed successfully")
                else:
                    print(f"❌ Batch crawl failed: {result['error']}")
            
            else:
                print(f"❌ Unknown command: {command}")
                sys.exit(1)
            
            # Show final stats
            stats = crawler.get_stats()
            print(f"\n📊 Final Statistics:")
            print(f"  Visited URLs: {stats['visited_urls']}")
            print(f"  Failed URLs: {stats['failed_urls']}")
            print(f"  Success Rate: {stats['success_rate']:.1f}%")
            
        except Exception as e:
            print(f"❌ Crawler error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()