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

    def check_login_status(self, context: BrowserContext) -> bool:
        """Check if the user is currently logged in to Trailhead."""
        try:
            self.logger.info("Checking login status...")

            # Use the existing page
            if not self.page:
                self.page = context.new_page()

            self.page.goto("https://trailhead.salesforce.com/home", timeout=30000)

            # Wait for page to load
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # Check for logged-in indicators (user is logged in if these are found)
            logged_in_indicators = [
                "[data-testid='user-menu']",
                ".user-menu",
                ".profile-menu",
                "[data-testid='profile']",
                ".profile",
                ".user-profile",
                "[data-testid='avatar']",
                ".avatar",
                ".user-avatar",
                "img[alt*='profile']",
                "img[alt*='avatar']",
                ".user-info",
                ".user-details",
                "[data-testid='user-info']",
                ".trailhead-user",
                ".user-dropdown",
                ".account-menu",
            ]

            for selector in logged_in_indicators:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"User is logged in: found {selector}")
                        return True
                except:
                    continue

            # Check for logged-out indicators (user is not logged in if these are found)
            logged_out_indicators = [
                "[data-testid='login-button']",
                ".login-button",
                "a[href*='login']",
                "button:has-text('Log In')",
                "button:has-text('Sign In')",
                "a:has-text('Log In')",
                "a:has-text('Sign In')",
                ".login-link",
                ".signin-button",
                "[data-testid='signin']",
            ]

            for selector in logged_out_indicators:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"User is not logged in: found {selector}")
                        return False
                except:
                    continue

            # If we can't determine status, check the URL
            current_url = self.page.url
            if "login" in current_url or "sessions" in current_url:
                self.logger.info(
                    f"User is not logged in: current URL contains login/sessions: {current_url}"
                )
                return False
            elif "home" in current_url or "trailhead.salesforce.com" in current_url:
                self.logger.info(
                    f"User appears to be logged in: current URL: {current_url}"
                )
                return True

            self.logger.warning("Could not determine login status")
            return False

        except Exception as e:
            self.logger.error(f"Login status check failed: {e}")
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
                    self.page = self.context.new_page()

                    if self.check_login_status(self.context):
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

            # Check if already logged in
            if self.check_login_status(self.context):
                self.logger.info("Already logged in, no need for login process")
                duration = time.time() - start_time
                log_performance("login_skip", duration, email=email)

                self.logger.end_operation("login", success=True, session_restored=False)
                return LoginResult(
                    browser_context=self.context,
                    page=self.page,
                    session_restored=False,
                    is_logged_in=True,
                )

            # Navigate directly to login URL instead of clicking button
            self.logger.info("Navigating directly to login URL...")
            self.page.goto(
                "https://trailhead.salesforce.com/sessions/users/new?type=tbidlogin",
                timeout=30000,
            )
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # Wait a bit more for any dynamic content
            time.sleep(3)

            # Enter email
            email_input_selectors = [
                "#field",  # Specific ID from the login form
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "#username",
                "#email",
            ]

            email_entered = False
            for selector in email_input_selectors:
                try:
                    elements = self.page.locator(selector).all()
                    self.logger.info(
                        f"Found {len(elements)} elements for selector: {selector}"
                    )

                    for i, element in enumerate(elements):
                        if element.is_visible():
                            self.logger.info(
                                f"Found visible email input: {selector} (element {i})"
                            )
                            element.fill(email)
                            email_entered = True
                            break

                    if email_entered:
                        break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            if not email_entered:
                # Debug: Log all input elements on the page
                all_inputs = self.page.locator("input").all()
                self.logger.error(
                    f"No email input found. Total inputs on page: {len(all_inputs)}"
                )
                for i, inp in enumerate(all_inputs):
                    try:
                        input_type = inp.get_attribute("type") or "text"
                        input_name = inp.get_attribute("name") or "no-name"
                        input_id = inp.get_attribute("id") or "no-id"
                        is_visible = inp.is_visible()
                        self.logger.error(
                            f"Input {i}: type={input_type}, name={input_name}, id={input_id}, visible={is_visible}"
                        )
                    except:
                        pass
                raise Exception("Could not find email input field")

            # Submit email form
            submit_selectors = [
                "button[type='submit'][part='button']",  # Specific Trailhead submit button
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Log In')",
                "button:has-text('Sign In')",
                ".login-submit",
            ]

            submitted = False
            for selector in submit_selectors:
                try:
                    elements = self.page.locator(selector).all()
                    self.logger.info(
                        f"Found {len(elements)} elements for submit selector: {selector}"
                    )

                    for i, element in enumerate(elements):
                        try:
                            if element.is_visible():
                                self.logger.info(
                                    f"Found visible submit button: {selector} (element {i})"
                                )

                                # Wait for any loading states to clear
                                try:
                                    self.page.wait_for_selector(
                                        "lwc-idx-loading", state="hidden", timeout=10000
                                    )
                                except:
                                    pass  # Loading element might not exist

                                # Try multiple click strategies
                                try:
                                    # Strategy 1: Force click
                                    element.click(force=True)
                                    self.logger.info("Force click successful")
                                    submitted = True
                                    break
                                except Exception as e1:
                                    self.logger.debug(f"Force click failed: {e1}")
                                    try:
                                        # Strategy 2: Click with timeout
                                        element.click(timeout=10000)
                                        self.logger.info("Regular click successful")
                                        submitted = True
                                        break
                                    except Exception as e2:
                                        self.logger.debug(f"Regular click failed: {e2}")
                                        try:
                                            # Strategy 3: JavaScript click
                                            self.page.evaluate(
                                                "arguments[0].click();", element
                                            )
                                            self.logger.info(
                                                "JavaScript click successful"
                                            )
                                            submitted = True
                                            break
                                        except Exception as e3:
                                            self.logger.debug(
                                                f"JavaScript click failed: {e3}"
                                            )
                                            # Strategy 4: Try clicking the span inside the button
                                            try:
                                                span_element = element.locator(
                                                    "span"
                                                ).first
                                                if span_element.is_visible():
                                                    span_element.click(force=True)
                                                    self.logger.info(
                                                        "Span click successful"
                                                    )
                                                    submitted = True
                                                    break
                                                else:
                                                    raise Exception("Span not visible")
                                            except Exception as e4:
                                                self.logger.debug(
                                                    f"All click strategies failed: {e4}"
                                                )
                                                continue
                        except Exception as e:
                            self.logger.debug(f"Error with submit element {i}: {e}")
                            continue

                    if submitted:
                        break
                except Exception as e:
                    self.logger.debug(f"Error with submit selector {selector}: {e}")
                    continue

            if not submitted:
                # Debug: Log all button elements on the page
                all_buttons = self.page.locator(
                    "button, input[type='submit'], lwc-wes-button"
                ).all()
                self.logger.error(
                    f"No submit button found. Total buttons on page: {len(all_buttons)}"
                )
                for i, btn in enumerate(all_buttons):
                    try:
                        button_text = btn.text_content() or "no-text"
                        button_type = btn.get_attribute("type") or "no-type"
                        button_tag = btn.evaluate("el => el.tagName.toLowerCase()")
                        is_visible = btn.is_visible()
                        self.logger.error(
                            f"Button {i}: tag={button_tag}, text='{button_text}', type={button_type}, visible={is_visible}"
                        )
                    except:
                        pass
                raise Exception("Could not find submit button")

            # Wait for verification code page
            self.page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)  # Wait for any redirects and page transitions

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
                "#field",  # Specific ID from the verification form
                "input[name='otp']",  # OTP field name
                "input[type='text']",
                "input[type='number']",
                "input[type='tel']",
                "input[name='code']",
                "input[name='verification']",
                "input[placeholder*='code']",
                "input[placeholder*='verification']",
                "input[placeholder*='OTP']",
                "#code",
                "#verification",
                "#otp",
                "[data-testid*='code']",
                "[data-testid*='verification']",
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

            # If no specific field found, try to find any input that could accept a code
            if not code_entered:
                self.logger.info(
                    "No specific verification field found, looking for any suitable input..."
                )
                all_inputs = self.page.locator("input").all()
                for input_elem in all_inputs:
                    try:
                        if input_elem.is_visible():
                            input_type = input_elem.get_attribute("type") or "text"
                            # Look for text, number, or tel inputs that are visible
                            if input_type in ["text", "number", "tel"]:
                                self.logger.info(
                                    f"Using fallback input field with type: {input_type}"
                                )
                                input_elem.fill(verification_code)
                                code_entered = True
                                break
                    except:
                        continue

            if not code_entered:
                raise Exception("Could not find verification code input field")

            # Submit verification code
            verify_selectors = [
                "lwc-wes-button",  # Specific Trailhead custom button
                "lwc-wes-button:has-text('Submit code')",  # Button with specific text
                "button[type='submit'][part='button']",  # Specific Trailhead button
                "button[type='submit']",
                "button:has-text('Verify')",
                "button:has-text('Submit')",
                "button:has-text('Submit code')",
                "button:has-text('Continue')",
                ".verify-button",
            ]

            submitted = False
            for selector in verify_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        self.logger.info(f"Found verify button: {selector}")

                        # Wait for any loading states to clear
                        try:
                            self.page.wait_for_selector(
                                "lwc-idx-loading", state="hidden", timeout=10000
                            )
                        except:
                            pass  # Loading element might not exist

                        # Try multiple click strategies
                        try:
                            # Strategy 1: Force click
                            element.click(force=True)
                            self.logger.info("Force click successful")
                            submitted = True
                            break
                        except Exception as e1:
                            self.logger.debug(f"Force click failed: {e1}")
                            try:
                                # Strategy 2: Click with timeout
                                element.click(timeout=10000)
                                self.logger.info("Regular click successful")
                                submitted = True
                                break
                            except Exception as e2:
                                self.logger.debug(f"Regular click failed: {e2}")
                                try:
                                    # Strategy 3: JavaScript click
                                    self.page.evaluate("arguments[0].click();", element)
                                    self.logger.info("JavaScript click successful")
                                    submitted = True
                                    break
                                except Exception as e3:
                                    self.logger.debug(f"JavaScript click failed: {e3}")
                                    # Strategy 4: Try clicking the span inside the button
                                    try:
                                        span_element = element.locator("span").first
                                        if span_element.is_visible():
                                            span_element.click(force=True)
                                            self.logger.info("Span click successful")
                                            submitted = True
                                            break
                                        else:
                                            raise Exception("Span not visible")
                                    except Exception as e4:
                                        self.logger.debug(
                                            f"All click strategies failed: {e4}"
                                        )
                                        continue
                except:
                    continue

            if not submitted:
                raise Exception("Could not find verification submit button")

            # Wait for login to complete
            self.page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)  # Additional wait for any redirects

            # Verify login success
            if self.check_login_status(self.context):
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
