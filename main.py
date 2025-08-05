import os
import sys
import dotenv

from salesforce.auth import SalesforceAuth
from crawl import TrailheadCrawler

# Default module URL for testing
DEFAULT_MODULE_URL = "https://trailhead.salesforce.com/content/learn/modules/starting_force_com"


def print_crawl_summary(crawl_data: dict) -> None:
    """Print a summary of crawled module data."""
    if not crawl_data:
        return
    
    module = crawl_data.get('module', {})
    lessons = crawl_data.get('lessons', [])
    
    print("\n🎉 Module crawl completed!")
    print(f"📚 Module: {module.get('title', 'N/A')}")
    print(f"📄 Description: {module.get('description', 'N/A')[:100]}...")
    print(f"📝 Lessons crawled: {len(lessons)}")
    
    if lessons:
        print(f"📖 Lesson details:")
        for i, lesson in enumerate(lessons, 1):
            print(f"  {i}. {lesson.get('title', 'N/A')}")
            print(f"     Content items: {len(lesson.get('content', []))}")
            print(f"     Learning objectives: {len(lesson.get('learning_objectives', []))}")
            print(f"     Instructions: {len(lesson.get('instructions', []))}")


def handle_module_crawl(email: str, module_url: str = DEFAULT_MODULE_URL, use_saved_session: bool = True) -> None:
    """Handle login process and crawl the specified module."""
    crawler = TrailheadCrawler()
    
    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)
            
            if result.session_restored:
                print("🎉 Session restored! Starting module crawl...")
            elif result.is_logged_in:
                print("🎉 Login completed! Starting module crawl...")
            else:
                print(f"❌ Login failed: {result.error}")
                return
            
            # Crawl the specified module
            print(f"\n🔍 Starting comprehensive crawl of module...")
            crawl_data = crawler.crawl_module(module_url, auth)
            
            if crawl_data:
                print_crawl_summary(crawl_data)
                
                # Show crawling statistics
                stats = crawler.get_stats()
                print(f"\n📊 Crawl Statistics:")
                print(f"  Total URLs processed: {stats['visited_urls']}")
                print(f"  Failed URLs: {stats['failed_urls']}")
                print(f"  Success rate: {stats['success_rate']:.1f}%")
                print(f"  Data saved to: {stats['output_directory']}")
            else:
                print("❌ Failed to crawl module")
                
        except Exception as e:
            print(f"❌ Error: {e}")


def handle_trail_crawl(email: str, trail_url: str, use_saved_session: bool = True) -> None:
    """Handle login process and crawl an entire trail."""
    crawler = TrailheadCrawler()
    
    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)
            
            if result.session_restored:
                print("🎉 Session restored! Starting trail crawl...")
            elif result.is_logged_in:
                print("🎉 Login completed! Starting trail crawl...")
            else:
                print(f"❌ Login failed: {result.error}")
                return
            
            # Crawl the trail
            print(f"\n🛤️  Starting comprehensive crawl of trail...")
            trail_data = crawler.crawl_trail(trail_url, auth)
            
            if 'error' not in trail_data:
                print(f"\n🎉 Trail crawl completed!")
                trail_info = trail_data.get('trail', {})
                modules = trail_data.get('modules', [])
                
                print(f"🛤️  Trail: {trail_info.get('title', 'N/A')}")
                print(f"📚 Modules processed: {len(modules)}")
                
                # Show statistics
                stats = crawler.get_stats()
                print(f"\n📊 Crawl Statistics:")
                print(f"  Total URLs processed: {stats['visited_urls']}")
                print(f"  Failed URLs: {stats['failed_urls']}")
                print(f"  Success rate: {stats['success_rate']:.1f}%")
                print(f"  Data saved to: {stats['output_directory']}")
            else:
                print(f"❌ Trail crawl failed: {trail_data['error']}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


def handle_batch_crawl(email: str, urls_file: str, use_saved_session: bool = True) -> None:
    """Handle login process and batch crawl URLs from file."""
    if not os.path.exists(urls_file):
        print(f"❌ URLs file not found: {urls_file}")
        return
    
    crawler = TrailheadCrawler()
    
    with SalesforceAuth() as auth:
        try:
            result = auth.login(email, use_saved_session)
            
            if result.session_restored:
                print("🎉 Session restored! Starting batch crawl...")
            elif result.is_logged_in:
                print("🎉 Login completed! Starting batch crawl...")
            else:
                print(f"❌ Login failed: {result.error}")
                return
            
            # Batch crawl
            print(f"\n📋 Starting batch crawl from {urls_file}...")
            batch_results = crawler.crawl_urls_from_file(urls_file, auth)
            
            if 'error' not in batch_results:
                print(f"\n🎉 Batch crawl completed!")
                print(f"📊 URLs processed: {len(batch_results)}")
                
                # Show statistics
                stats = crawler.get_stats()
                print(f"\n📊 Final Statistics:")
                print(f"  Total URLs processed: {stats['visited_urls']}")
                print(f"  Failed URLs: {stats['failed_urls']}")
                print(f"  Success rate: {stats['success_rate']:.1f}%")
                print(f"  Data saved to: {stats['output_directory']}")
            else:
                print(f"❌ Batch crawl failed: {batch_results['error']}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


def show_crawler_stats():
    """Show crawling statistics."""
    crawler = TrailheadCrawler()
    stats = crawler.get_stats()
    print(f"📊 Crawling Statistics:")
    print(f"  Visited URLs: {stats['visited_urls']}")
    print(f"  Failed URLs: {stats['failed_urls']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  Output Directory: {stats['output_directory']}")


def clear_session():
    """Clear saved session."""
    with SalesforceAuth() as auth:
        auth.clear_session()


def print_help():
    """Print usage information."""
    print("TrailBuster - Salesforce Trailhead Automation Tool")
    print()
    print("Usage:")
    print("  python main.py <module_url>           - Crawl a single module")
    print("  python main.py trail <trail_url>      - Crawl an entire trail")
    print("  python main.py batch <urls_file>      - Batch crawl URLs from file")
    print()
    print("Options:")
    print("  python main.py stats                  - Show crawling statistics")
    print("  python main.py --clear-session        - Clear saved session")
    print("  python main.py --no-session           - Force new login (ignore saved session)")
    print("  python main.py --help                 - Show this help message")
    print()
    print("Examples:")
    print("  python main.py https://trailhead.salesforce.com/content/learn/modules/starting_force_com")
    print("  python main.py trail https://trailhead.salesforce.com/trails/force_com_admin_beginner")
    print("  python main.py batch sample_urls.txt")
    print()
    print("All crawled content is structured for LLM processing and saved to the 'crawled_data' directory.")


def main():
    """Main entry point for TrailBuster."""
    dotenv.load_dotenv()
    email = os.getenv("SALESFORCE_EMAIL")
    
    if not email:
        print("❌ SALESFORCE_EMAIL not found in environment variables")
        print("Please add SALESFORCE_EMAIL=your_email@example.com to your .env file")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) == 1:
        # Default behavior: crawl default module
        print("🔍 No URL specified, crawling default module...")
        handle_module_crawl(email)
        return
    
    command = sys.argv[1]
    
    # Help command
    if command in ["--help", "-h", "help"]:
        print_help()
        return
    
    # Session management commands
    if command == "--clear-session":
        clear_session()
        return
    
    # Statistics command
    elif command == "stats":
        show_crawler_stats()
        return
    
    # Trail crawling command
    elif command == "trail":
        if len(sys.argv) < 3:
            print("❌ Trail URL required for trail command")
            print("Usage: python main.py trail <trail_url>")
            sys.exit(1)
        
        trail_url = sys.argv[2]
        use_saved_session = "--no-session" not in sys.argv
        handle_trail_crawl(email, trail_url, use_saved_session)
        return
    
    # Batch crawling command
    elif command == "batch":
        if len(sys.argv) < 3:
            print("❌ URLs file required for batch command")
            print("Usage: python main.py batch <urls_file>")
            sys.exit(1)
        
        urls_file = sys.argv[2]
        use_saved_session = "--no-session" not in sys.argv
        handle_batch_crawl(email, urls_file, use_saved_session)
        return
    
    # Check for --no-session flag
    use_saved_session = "--no-session" not in sys.argv
    
    # If first argument looks like a URL, treat it as a module URL
    if command.startswith("http"):
        module_url = command
        handle_module_crawl(email, module_url, use_saved_session)
        return
    
    # Unknown command
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python main.py --help' for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()