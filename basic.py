from pydantic import BaseModel
import os
import dotenv
from playwright.sync_api import sync_playwright
import time

from salesforce_auth import clear_saved_session, login_to_trailhead

# Good beginner trail to test out
TRAIL_URL = "https://trailhead.salesforce.com/content/learn/modules/starting_force_com"


def read_trail_module(page, module_url: str = TRAIL_URL):
    """
    Navigate to and read a Trailhead module
    """
    try:
        print(f"Navigating to module: {module_url}")
        page.goto(module_url)

        # Wait for the page to load
        page.wait_for_load_state("networkidle", timeout=100000)
        time.sleep(3)  # Wait for dynamic content

        print("Module page loaded successfully!")

        # Extract module information
        module_info = {}

        # Try to get the module title
        try:
            title_selectors = [
                "h1",
                "[data-testid='module-title']",
                ".module-title",
                ".trailhead-title",
            ]

            for selector in title_selectors:
                title_element = page.locator(selector).first
                if title_element.is_visible():
                    module_info["title"] = title_element.text_content().strip()
                    print(f"Module Title: {module_info['title']}")
                    break
        except Exception as e:
            print(f"Could not extract title: {e}")

        # Try to get the module description
        try:
            desc_selectors = [
                "[data-testid='module-description']",
                ".module-description",
                ".trailhead-description",
                "p:first-of-type",
            ]

            for selector in desc_selectors:
                desc_element = page.locator(selector).first
                if desc_element.is_visible():
                    module_info["description"] = desc_element.text_content().strip()
                    print(f"Module Description: {module_info['description']}")
                    break
        except Exception as e:
            print(f"Could not extract description: {e}")

        # Get the page content
        try:
            # Get the main content area
            content_selectors = [
                "main",
                ".module-content",
                ".trailhead-content",
                "[role='main']",
            ]

            content_element = None
            for selector in content_selectors:
                content_element = page.locator(selector).first
                if content_element.is_visible():
                    break

            if content_element:
                module_info["content"] = content_element.text_content().strip()
                print(f"Content length: {len(module_info['content'])} characters")
            else:
                # Fallback: get body content
                module_info["content"] = page.locator("body").text_content().strip()
                print(f"Body content length: {len(module_info['content'])} characters")

        except Exception as e:
            print(f"Could not extract content: {e}")

        # Check for units/chapters in the module
        try:
            unit_selectors = ["[data-testid='unit']", ".unit", ".chapter", ".lesson"]

            units = []
            for selector in unit_selectors:
                unit_elements = page.locator(selector).all()
                if unit_elements:
                    for unit in unit_elements[:5]:  # Limit to first 5 units
                        try:
                            unit_text = unit.text_content().strip()
                            if unit_text:
                                units.append(unit_text)
                        except:
                            continue
                    break

            if units:
                module_info["units"] = units
                print(f"Found {len(units)} units/chapters")

        except Exception as e:
            print(f"Could not extract units: {e}")

        # Get current URL for reference
        module_info["url"] = page.url
        print(f"Current URL: {module_info['url']}")

        return module_info

    except Exception as e:
        print(f"Error reading module: {e}")
        return None


def read_module_with_session(module_url: str = TRAIL_URL):
    """
    Read a Trailhead module using an existing saved session
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)

    if os.path.exists("trailhead_session.json"):
        print("Loading saved session for module reading...")
        context = browser.new_context(storage_state="trailhead_session.json")
        page = context.new_page()

        try:
            # Check if session is still valid
            page.goto("https://trailhead.salesforce.com/home")
            page.wait_for_load_state("networkidle", timeout=10000)

            current_url = page.url
            if "login" in current_url or "sessions" in current_url:
                print("❌ Session expired. Please run the full login process first.")
                return None

            print("✅ Session valid, reading module...")
            module_info = read_trail_module(page, module_url)
            return module_info

        except Exception as e:
            print(f"Error reading module with session: {e}")
            return None
        finally:
            browser.close()
    else:
        print("❌ No saved session found. Please run the full login process first.")
        browser.close()
        return None


# def read_trail_content(url: str) -> TrailheadDocument:
#     pass


# def create_action_plan(content: TrailheadDocument) -> ActionPlan:
#     pass


if __name__ == "__main__":
    import sys

    dotenv.load_dotenv()
    email = os.getenv("SALESFORCE_EMAIL")

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear-session":
            clear_saved_session()
            exit(0)
        elif sys.argv[1] == "--no-session":
            auth_metadata = login_to_trailhead(email, use_saved_session=False)
        elif sys.argv[1] == "--read-module":
            # Read module using existing session
            module_info = read_module_with_session()
            if module_info:
                print("\n✅ Module read successfully!")
                print(f"Title: {module_info.get('title', 'N/A')}")
                print(f"Description: {module_info.get('description', 'N/A')[:100]}...")
                print(
                    f"Content length: {len(module_info.get('content', ''))} characters"
                )

                # Save module info to file
                try:
                    import json

                    with open("module_info.json", "w") as f:
                        json.dump(module_info, f, indent=2)
                    print("💾 Module information saved to module_info.json")
                except Exception as e:
                    print(f"Could not save module info: {e}")
            exit(0)
        else:
            print("Usage: python basic.py [--clear-session|--no-session|--read-module]")
            print("  --clear-session: Clear saved session")
            print("  --no-session: Force new login without using saved session")
            print("  --read-module: Read module using existing session")
            exit(1)
    else:
        auth_metadata = login_to_trailhead(email, use_saved_session=True)

    if auth_metadata and auth_metadata.get("session_restored"):
        print("🎉 Session restored! You can now continue with your automation.")
    elif auth_metadata:
        print("🎉 Login completed! Session saved for next time.")

    # Read the Starting Force.com module
    if auth_metadata and auth_metadata.get("page"):
        print("\n📚 Reading Starting Force.com module...")
        module_info = read_trail_module(auth_metadata["page"])

        if module_info:
            print("\n✅ Module read successfully!")
            print(f"Title: {module_info.get('title', 'N/A')}")
            print(f"Description: {module_info.get('description', 'N/A')[:100]}...")
            print(f"Content length: {len(module_info.get('content', ''))} characters")

            # Save module info to file
            try:
                import json

                with open("module_info.json", "w") as f:
                    json.dump(module_info, f, indent=2)
                print("💾 Module information saved to module_info.json")
            except Exception as e:
                print(f"Could not save module info: {e}")
        else:
            print("❌ Failed to read module")

    # action_plan = create_action_plan(content)
