import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, BrowserContext, Locator, Page, sync_playwright

from salesforce.auth_code import get_salesforce_auth_code
from trailbuster.logger import get_logger, log_auth, log_performance


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

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.logger = get_logger("AUTH")

        # Session file path
        self.session_file = "trailhead_session.json"
        self.token_file = "token.json"

    def __enter__(self):
        """Context manager entry."""
        self._start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._close_browser()

    def _start_browser(self) -> None:
        """Start the browser instance."""
        try:
            self.logger.start_operation("browser_startup", headless=self.headless)

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            self.logger.info("Browser started successfully")
            self.logger.end_operation("browser_startup", success=True)

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            self.logger.end_operation("browser_startup", success=False, error=str(e))
            raise

    def _close_browser(self) -> None:
        """Close the browser instance."""
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, "playwright"):
                self.playwright.stop()

            self.logger.info("Browser closed successfully")

        except Exception as e:
            self.logger.warning(f"Error closing browser: {e}")

    def _create_context(self, storage_state: Optional[str] = None) -> BrowserContext:
        """Create a browser context with optional session storage."""
        try:
            action = "Loading" if storage_state else "Creating"
            self.logger.info(f"{action} browser context...")

            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }

            if storage_state and os.path.exists(storage_state):
                context_options["storage_state"] = storage_state

            self.context = self.browser.new_context(**context_options)
            return self.context

        except Exception as e:
            self.logger.error(f"Failed to create browser context: {e}")
            raise

    def check_session_validity(self, context: BrowserContext) -> bool:
        """Check if the saved session is still valid."""
        try:
            self.logger.info("Checking session validity...")

            page = context.new_page()
            page.goto("https://trailhead.salesforce.com/", timeout=30000)

            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=10000)

            # Check for login indicators
            login_indicators = [
                "[data-testid='user-menu']",
                ".user-menu",
                ".profile-menu",
                "[data-testid='profile']",
                ".profile",
            ]

            for selector in login_indicators:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Session valid: found {selector}")
                        page.close()
                        return True
                except:
                    continue

            # Check for logout/login buttons (indicates not logged in)
            logout_indicators = [
                "[data-testid='login-button']",
                ".login-button",
                "a[href*='login']",
            ]

            for selector in logout_indicators:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Login required: found {selector}")
                        page.close()
                        return False
                except:
                    continue

            page.close()
            return False

        except Exception as e:
            self.logger.error(f"Session check failed: {e}")
            return False

    def login(self, email: str, use_saved_session: bool = True) -> LoginResult:
        """Perform login to Salesforce Trailhead."""
        start_time = time.time()
        self.logger.start_operation(
            "login", email=email, use_saved_session=use_saved_session
        )

        try:
            # Try to restore session if requested
            if use_saved_session and os.path.exists(self.session_file):
                try:
                    self.context = self._create_context(self.session_file)

                    if self.check_session_validity(self.context):
                        self.page = self.context.new_page()

                        duration = time.time() - start_time
                        log_performance("session_restore", duration, email=email)

                        self.logger.info("Session restored successfully")
                        self.logger.end_operation(
                            "login", success=True, session_restored=True
                        )

                        return LoginResult(
                            browser_context=self.context,
                            page=self.page,
                            session_restored=True,
                            is_logged_in=True,
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to restore session: {e}")

            # Perform fresh login
            self.logger.info("Starting login process...")
            self.context = self._create_context()
            self.page = self.context.new_page()

            # Navigate to login page
            self.page.goto("https://trailhead.salesforce.com/", timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # Click login button
            login_button_selectors = [
                "[data-testid='login-button']",
                ".login-button",
                "a[href*='login']",
                "button:has-text('Log In')",
                "a:has-text('Log In')",
            ]

            login_clicked = False
            for selector in login_button_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Found login button: {selector}")
                        element.click()
                        login_clicked = True
                        break
                except:
                    continue

            if not login_clicked:
                raise Exception("Could not find login button")

            # Wait for login form
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # Enter email
            email_input_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input[data-testid='email-input']",
                "#email",
            ]

            email_entered = False
            for selector in email_input_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Found email input: {selector}")
                        element.fill(email)
                        email_entered = True
                        break
                except:
                    continue

            if not email_entered:
                raise Exception("Could not find email input field")

            # Submit email form
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Continue')",
                "button:has-text('Next')",
            ]

            submitted = False
            for selector in submit_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Found submit button: {selector}")
                        element.click()
                        submitted = True
                        break
                except:
                    continue

            if not submitted:
                raise Exception("Could not find submit button")

            # Wait for verification code page
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # Check for reCAPTCHA
            if self._check_for_recaptcha():
                self.logger.warning("reCAPTCHA detected - manual intervention required")
                input("Please complete the reCAPTCHA and press Enter to continue...")

            # Get verification code from Gmail
            self.logger.info("Retrieving verification code...")
            verification_code = get_salesforce_auth_code()

            if not verification_code:
                raise Exception("Failed to retrieve verification code")

            self.logger.info(f"Got verification code: {verification_code}")

            # Enter verification code
            code_input_selectors = [
                "input[type='text']",
                "input[name='code']",
                "input[data-testid='verification-code']",
                "#verificationCode",
            ]

            code_entered = False
            for selector in code_input_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Found verification code input: {selector}")
                        element.fill(verification_code)
                        code_entered = True
                        break
                except:
                    continue

            if not code_entered:
                raise Exception("Could not find verification code input field")

            # Submit verification code
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Verify')",
                "button:has-text('Submit')",
            ]

            submitted = False
            for selector in submit_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(
                            f"Found verification submit button: {selector}"
                        )
                        element.click()
                        submitted = True
                        break
                except:
                    continue

            if not submitted:
                raise Exception("Could not find verification submit button")

            # Wait for login to complete
            self.page.wait_for_load_state("networkidle", timeout=30000)

            # Verify login success
            if self.check_session_validity(self.context):
                self.logger.info("Login completed successfully!")

                # Save session
                self._save_session()

                duration = time.time() - start_time
                log_performance("login", duration, email=email)

                self.logger.end_operation("login", success=True, session_restored=False)

                return LoginResult(
                    browser_context=self.context,
                    page=self.page,
                    session_restored=False,
                    is_logged_in=True,
                )
            else:
                raise Exception("Login verification failed")

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            self.logger.end_operation("login", success=False, error=str(e))

            return LoginResult(
                browser_context=self.context,
                page=self.page,
                session_restored=False,
                is_logged_in=False,
                error=str(e),
            )

    def _find_element(
        self, selectors: List[str], element_type: str
    ) -> Optional[Locator]:
        """Find an element using multiple selectors."""
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    self.logger.info(f"Found {element_type}: {selector}")
                    return element
            except:
                continue

        self.logger.warning(f"Could not find {element_type}")
        return None

    def _click_element(
        self, element: Locator, element_name: str, max_attempts: int = 3
    ) -> bool:
        """Click an element with retry logic."""
        for i in range(max_attempts):
            try:
                self.logger.info(f"Clicking {element_name}...")
                element.click()
                self.logger.info(f"Click strategy {i + 1} successful")
                return True
            except Exception as e:
                self.logger.warning(f"Click strategy {i + 1} failed: {e}")
                if i < max_attempts - 1:
                    time.sleep(1)

        self.logger.error(f"All click strategies failed for {element_name}")
        return False

    def _check_for_recaptcha(self) -> bool:
        """Check if reCAPTCHA is present on the page."""
        self.logger.info("Checking for reCAPTCHA...")

        recaptcha_selectors = [
            ".g-recaptcha",
            "#recaptcha",
            "iframe[src*='recaptcha']",
            "[data-testid='recaptcha']",
        ]

        for selector in recaptcha_selectors:
            try:
                element = self.page.locator(selector).first
                if element.is_visible():
                    self.logger.info(f"reCAPTCHA detected: {selector}")
                    return True
            except:
                continue

        self.logger.info("No reCAPTCHA detected")
        return False

    def _save_session(self) -> None:
        """Save the current session state."""
        try:
            self.context.storage_state(path=self.session_file)
            self.logger.info("Session saved successfully!")
        except Exception as e:
            self.logger.warning(f"Could not save session: {e}")

    def clear_session(self) -> None:
        """Clear saved session data."""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                self.logger.info("Session cleared successfully!")
            else:
                self.logger.info("No saved session found")
        except Exception as e:
            self.logger.error(f"Error clearing session: {e}")

    def get_page(self) -> Page:
        """Get the current page instance."""
        if not self.page:
            raise Exception("No page available. Call login() first.")
        return self.page

    def _navigate_with_retry(self, url: str, max_retries: int = 3) -> None:
        """Navigate to URL with retry logic."""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Navigation attempt {attempt + 1}/{max_retries}")
                self.page.goto(url, wait_until="networkidle", timeout=30000)
                return
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise
