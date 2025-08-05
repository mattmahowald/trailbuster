import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Locator
from salesforce.auth_code import get_salesforce_auth_code


@dataclass
class LoginResult:
    """Result of a login attempt."""
    browser_context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    session_restored: bool = False
    is_logged_in: bool = False
    error: Optional[str] = None


class SalesforceAuth:
    """Manages Salesforce Trailhead authentication and browser sessions."""
    
    LOGIN_URL = "https://trailhead.salesforce.com/sessions/users/new?type=tbidlogin"
    HOME_URL = "https://trailhead.salesforce.com/home"
    
    # Element selectors organized by purpose
    SELECTORS = {
        'username': ["#field", "input[type='email']", "input[name='email']", "input[name='username']"],
        'submit': ["button[type='submit'][part='button']", "button[type='submit']", "button:has-text('Log In')"],
        'verification': ["#field", "input[name='otp']", "input[type='text']", "input[type='number']", "input[name='code']"],
        'verify_button': ["lwc-wes-button", "button[type='submit'][part='button']", "button:has-text('Verify')", "button:has-text('Submit')"],
        'recaptcha': ["iframe[src*='recaptcha']", ".g-recaptcha", "#recaptcha", "[data-sitekey]"],
        'logged_in': ["[data-testid='user-menu']", ".user-menu", ".profile-menu", "[data-testid='profile']", ".avatar"],
        'login_button': ["a[href='/login']", "a:has-text('Login')", "button:has-text('Log In')"]
    }

    def __init__(self, headless: bool = False, session_file: str = "trailhead_session.json"):
        self.headless = headless
        self.session_file = session_file
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_logged_in = False
        self._keep_alive = False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if not self._keep_alive:
            self.close()

    def keep_alive(self):
        """Mark the browser session to stay alive."""
        self._keep_alive = True

    def force_close(self):
        """Force close the browser session."""
        self._keep_alive = False
        self.close()

    def start(self):
        """Start the browser instance."""
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            print("✅ Browser started")

    def close(self):
        """Close browser and clean up resources."""
        for resource, name in [(self.browser, "browser"), (self.playwright, "playwright")]:
            if resource:
                try:
                    resource.close() if name == "browser" else resource.stop()
                except Exception as e:
                    print(f"Warning: Error closing {name}: {e}")
        print("✅ Browser closed")

    def create_context(self, use_saved_session: bool = True) -> BrowserContext:
        """Create a browser context with optional session restoration."""
        storage_state = self.session_file if (use_saved_session and os.path.exists(self.session_file)) else None
        print(f"{'Loading' if storage_state else 'Creating'} session...")
        
        self.context = self.browser.new_context(storage_state=storage_state)
        self.page = self.context.new_page()
        return self.context

    def check_session_validity(self) -> bool:
        """Check if the current session is still valid."""
        try:
            print("Checking session validity...")
            self._retry_navigation(self.HOME_URL)
            time.sleep(2)
            
            # Check for logged-in indicators
            for selector in self.SELECTORS['logged_in']:
                try:
                    if self.page.locator(selector).first.is_visible():
                        print(f"✅ Session valid: {selector}")
                        self.is_logged_in = True
                        return True
                except:
                    continue
            
            # Check for login buttons (indicates not logged in)
            for selector in self.SELECTORS['login_button']:
                try:
                    if self.page.locator(selector).first.is_visible():
                        print(f"❌ Login required: {selector}")
                        break
                except:
                    continue
            
            self.is_logged_in = False
            return False
        except Exception as e:
            print(f"Session check failed: {e}")
            self.is_logged_in = False
            return False

    def login(self, email: str, use_saved_session: bool = True) -> LoginResult:
        """Perform the complete login process."""
        try:
            self.create_context(use_saved_session)

            if use_saved_session and self.check_session_validity():
                return LoginResult(
                    browser_context=self.context,
                    page=self.page,
                    session_restored=True,
                    is_logged_in=True
                )

            return self._perform_login(email)
        except Exception as e:
            print(f"Login error: {e}")
            return LoginResult(
                browser_context=self.context,
                page=self.page,
                error=str(e)
            )
    
    def _perform_login(self, email: str) -> LoginResult:
        """Execute the login flow."""
        print("Starting login process...")
        self._retry_navigation(self.LOGIN_URL)
        
        # Enter email
        username_field = self._find_element('username', 'username field')
        if not username_field:
            raise Exception("Username field not found")
        
        username_field.fill(email)
        
        # Submit email
        submit_button = self._find_element('submit', 'submit button')
        if not submit_button or not self._click_element(submit_button, 'submit button'):
            raise Exception("Could not submit email")
        
        self.page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        
        # Handle reCAPTCHA
        self._handle_recaptcha()
        
        # Get and enter verification code
        print("Retrieving verification code...")
        time.sleep(10)
        verification_code = get_salesforce_auth_code()
        if not verification_code:
            raise Exception("No verification code received")
        
        print(f"Got verification code: {verification_code}")
        
        # Enter code
        code_field = self._find_element('verification', 'verification field') or self._find_fallback_input()
        if not code_field:
            raise Exception("Verification field not found")
        
        code_field.fill(verification_code)
        
        # Submit verification
        verify_button = self._find_element('verify_button', 'verify button')
        if not verify_button or not self._click_element(verify_button, 'verify button'):
            raise Exception("Could not submit verification code")
        
        # Wait for completion
        self.page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        
        print("Login completed!")
        self._save_session()
        self.is_logged_in = True
        
        return LoginResult(
            browser_context=self.context,
            page=self.page,
            is_logged_in=True
        )

    def _find_element(self, selector_key: str, element_type: str = None) -> Optional[Locator]:
        """Find an element using predefined selectors."""
        element_type = element_type or selector_key
        for selector in self.SELECTORS[selector_key]:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    print(f"Found {element_type}: {selector}")
                    return element
            except:
                continue
        print(f"Could not find {element_type}")
        return None

    def _click_element(self, element: Locator, element_name: str = "element") -> bool:
        """Click an element using multiple strategies."""
        print(f"Clicking {element_name}...")
        
        # Wait for loading to clear
        try:
            self.page.wait_for_selector("lwc-idx-loading", state="hidden", timeout=10000)
        except:
            pass

        strategies = [
            lambda: element.click(force=True),
            lambda: element.click(timeout=10000),
            lambda: self.page.evaluate("arguments[0].click();", element)
        ]

        for i, strategy in enumerate(strategies, 1):
            try:
                strategy()
                print(f"Click strategy {i} successful")
                return True
            except Exception as e:
                print(f"Click strategy {i} failed: {e}")
        
        print(f"All click strategies failed for {element_name}")
        return False

    def _handle_recaptcha(self) -> None:
        """Handle reCAPTCHA if present."""
        print("Checking for reCAPTCHA...")
        try:
            for selector in self.SELECTORS['recaptcha']:
                if self.page.locator(selector).count() > 0:
                    print(f"reCAPTCHA detected: {selector}")
                    input("Please solve reCAPTCHA and press Enter...")
                    return
            print("No reCAPTCHA detected")
        except Exception as e:
            print(f"reCAPTCHA check failed: {e}")

    def _find_fallback_input(self) -> Optional[Locator]:
        """Find any suitable input field as fallback."""
        print("Looking for fallback input...")
        
        suitable_types = {"text", "number", "tel"}
        for input_elem in self.page.locator("input").all():
            try:
                if input_elem.is_visible():
                    input_type = input_elem.get_attribute("type") or "text"
                    if input_type in suitable_types:
                        print(f"Using fallback input: {input_type}")
                        return input_elem
            except:
                continue
        return None

    def _save_session(self):
        """Save the current session state."""
        try:
            self.context.storage_state(path=self.session_file)
            print("✅ Session saved successfully!")
        except Exception as e:
            print(f"Warning: Could not save session: {e}")

    def clear_session(self):
        """Clear the saved session file."""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                print("✅ Session cleared!")
            else:
                print("No saved session found")
        except Exception as e:
            print(f"Error clearing session: {e}")

    def get_page(self) -> Optional[Page]:
        """Get the current page object."""
        return self.page

    def get_context(self) -> Optional[BrowserContext]:
        """Get the current browser context."""
        return self.context

    def _retry_navigation(self, url: str, max_retries: int = 3, timeout: int = 60000):
        """Retry navigation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                print(f"Navigation attempt {attempt + 1}/{max_retries}")
                self.page.goto(url, timeout=timeout)
                self.page.wait_for_load_state("networkidle", timeout=30000)
                return True
            except Exception as e:
                print(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise e
        return False


# Convenience functions for backward compatibility
def clear_saved_session():
    """Clear the saved session file."""
    auth = SalesforceAuth()
    auth.clear_session()


def login_to_trailhead(email: str, use_saved_session: bool = True):
    """Login to Trailhead (backward compatibility)."""
    with SalesforceAuth() as auth:
        result = auth.login(email, use_saved_session)
        return {
            "browser_context": result.browser_context,
            "page": result.page,
            "session_restored": result.session_restored,
            "is_logged_in": result.is_logged_in,
            "error": result.error
        }