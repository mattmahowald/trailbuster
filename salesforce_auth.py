from pydantic import BaseModel
import os
import dotenv
from playwright.sync_api import sync_playwright
import time
from salesforce_code import get_salesforce_auth_code

LOGIN_URL = "https://trailhead.salesforce.com/sessions/users/new?type=tbidlogin"


def clear_saved_session():
    """Clear the saved session file"""
    try:
        if os.path.exists("trailhead_session.json"):
            os.remove("trailhead_session.json")
            print("✅ Saved session cleared successfully!")
        else:
            print("No saved session found to clear.")
    except Exception as e:
        print(f"Error clearing session: {e}")


def login_to_trailhead(email: str, use_saved_session: bool = True):
    """
    Navigate to Trailhead and begin the login process using Playwright
    """
    playwright = sync_playwright().start()

    # Launch browser (you can change to 'firefox' or 'webkit' if needed)
    browser = playwright.chromium.launch(
        headless=False
    )  # Set headless=True for production

    # Create a new browser context with session persistence
    if use_saved_session and os.path.exists("trailhead_session.json"):
        print("Loading saved session...")
        context = browser.new_context(storage_state="trailhead_session.json")
    else:
        print("Creating new session...")
        context = browser.new_context()

    # Create a new page
    page = context.new_page()

    try:
        # First, try to navigate to a protected page to check if we're already logged in
        if use_saved_session:
            print("Checking if already logged in...")
            try:
                page.goto("https://trailhead.salesforce.com/home")
                page.wait_for_load_state("networkidle", timeout=10000)

                # Check if we're redirected to login page or if we see user-specific content
                current_url = page.url
                if "login" not in current_url and "sessions" not in current_url:
                    print("✅ Already logged in! Session restored successfully.")
                    return {
                        "browser_context": context,
                        "page": page,
                        "session_restored": True,
                    }
                else:
                    print("Session expired, proceeding with login...")
            except Exception as e:
                print(f"Session check failed: {e}, proceeding with login...")

        # Navigate to the Trailhead URL
        print(f"Navigating to: {LOGIN_URL}")
        page.goto(LOGIN_URL)

        # Wait for the page to load
        page.wait_for_load_state("networkidle", timeout=100000)

        # Look for username/email field
        username_selectors = [
            "#field",  # Specific ID from the login form
            "input[type='email']",
            "input[name='email']",
            "input[name='username']",
            "#username",
            "#email",
        ]

        username_field = None
        for selector in username_selectors:
            try:
                username_field = page.locator(selector).first
                if username_field.is_visible():
                    break
            except:
                continue

        if username_field:
            print("Found username field, entering credentials...")
            username_field.fill(email)

            # Look for submit button
            submit_selectors = [
                "button[type='submit'][part='button']",  # Specific Trailhead submit button
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Log In')",
                "button:has-text('Sign In')",
                ".login-submit",
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = page.locator(selector).first
                    if submit_button.is_visible():
                        break
                except:
                    continue

            if submit_button:
                print("Found submit button, attempting to click...")

                # Wait for any loading states to clear
                try:
                    page.wait_for_selector(
                        "lwc-idx-loading", state="hidden", timeout=100000
                    )
                except:
                    pass  # Loading element might not exist

                # Try multiple click strategies
                try:
                    # Strategy 1: Force click
                    submit_button.click(force=True)
                    print("Force click successful")
                except Exception as e1:
                    print(f"Force click failed: {e1}")
                    try:
                        # Strategy 2: Click with timeout and wait for navigation
                        submit_button.click(timeout=100000)
                        print("Regular click successful")
                    except Exception as e2:
                        print(f"Regular click failed: {e2}")
                        try:
                            # Strategy 3: JavaScript click
                            page.evaluate("arguments[0].click();", submit_button)
                            print("JavaScript click successful")
                        except Exception as e3:
                            print(f"JavaScript click failed: {e3}")
                            # Strategy 4: Try clicking the span inside the button
                            try:
                                span_element = submit_button.locator("span").first
                                if span_element.is_visible():
                                    span_element.click(force=True)
                                    print("Span click successful")
                                else:
                                    raise Exception("Span not visible")
                            except Exception as e4:
                                print(f"All click strategies failed: {e4}")
                                raise e4

                # Wait for the verification code page to load
                page.wait_for_load_state("networkidle", timeout=100000)
                time.sleep(3)  # Wait for any redirects and page transitions

                # Check for reCAPTCHA and solve it if present
                print("Checking for reCAPTCHA...")
                try:
                    recaptcha_present = False
                    recaptcha_selectors = [
                        "iframe[src*='recaptcha']",
                        ".g-recaptcha",
                        "#recaptcha",
                        "[data-sitekey]",
                        "iframe[title*='recaptcha']",
                    ]

                    for selector in recaptcha_selectors:
                        if page.locator(selector).count() > 0:
                            recaptcha_present = True
                            print(f"reCAPTCHA detected with selector: {selector}")
                            break

                    if recaptcha_present:
                        print("reCAPTCHA detected, please solve it manually.")
                        # Wait for user input to proceed
                        input("Press Enter when reCAPTCHA is solved...")
                        print("Continuing after manual reCAPTCHA intervention...")
                    else:
                        print("No reCAPTCHA detected, proceeding...")

                except Exception as e:
                    print(f"reCAPTCHA solving failed: {e}")
                    print("Continuing with the flow...")

                print("Email submitted, now waiting for verification code...")

                # Get the verification code from Gmail
                time.sleep(10)
                verification_code = get_salesforce_auth_code()

                # Wait for the verification code page to load properly
                print("Waiting for verification code page to load...")
                page.wait_for_load_state("networkidle", timeout=100000)
                time.sleep(3)  # Additional wait for dynamic content

                # Debug: Print all input fields on the page to help identify the correct selector
                print("Debug: Available input fields on the page:")
                all_inputs = page.locator("input").all()
                for i, input_elem in enumerate(all_inputs[:10]):  # Show first 10 inputs
                    try:
                        input_type = input_elem.get_attribute("type") or "text"
                        input_name = input_elem.get_attribute("name") or "no-name"
                        input_id = input_elem.get_attribute("id") or "no-id"
                        input_placeholder = (
                            input_elem.get_attribute("placeholder") or "no-placeholder"
                        )
                        print(
                            f"  Input {i+1}: type='{input_type}', name='{input_name}', id='{input_id}', placeholder='{input_placeholder}'"
                        )
                    except:
                        print(f"  Input {i+1}: Could not read attributes")

                if verification_code:
                    print(f"Retrieved verification code: {verification_code}")

                    # Look for verification code input field
                    code_selectors = [
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

                    code_field = None
                    for selector in code_selectors:
                        try:
                            code_field = page.locator(selector).first
                            if code_field.is_visible():
                                print(
                                    f"Found verification code field with selector: {selector}"
                                )
                                break
                        except:
                            continue

                    # If no specific field found, try to find any input that could accept a code
                    if not code_field:
                        print(
                            "No specific verification field found, looking for any suitable input..."
                        )
                        all_inputs = page.locator("input").all()
                        for input_elem in all_inputs:
                            try:
                                if input_elem.is_visible():
                                    input_type = (
                                        input_elem.get_attribute("type") or "text"
                                    )
                                    # Look for text, number, or tel inputs that are visible
                                    if input_type in ["text", "number", "tel"]:
                                        code_field = input_elem
                                        print(
                                            f"Using fallback input field with type: {input_type}"
                                        )
                                        break
                            except:
                                continue

                    if code_field:
                        print("Found verification code field, entering code...")
                        code_field.fill(verification_code)

                        # Look for submit/verify button
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

                        verify_button = None
                        for selector in verify_selectors:
                            try:
                                verify_button = page.locator(selector).first
                                if verify_button.is_visible():
                                    break
                            except:
                                continue

                        if verify_button:
                            print("Found verify button, attempting to click...")

                            # Wait for any loading states to clear
                            try:
                                page.wait_for_selector(
                                    "lwc-idx-loading", state="hidden", timeout=10000
                                )
                            except:
                                pass  # Loading element might not exist

                            # Try multiple click strategies
                            try:
                                # Strategy 1: Force click
                                verify_button.click(force=True)
                                print("Force click successful")
                            except Exception as e1:
                                print(f"Force click failed: {e1}")
                                try:
                                    # Strategy 2: Click with timeout
                                    verify_button.click(timeout=10000)
                                    print("Regular click successful")
                                except Exception as e2:
                                    print(f"Regular click failed: {e2}")
                                    try:
                                        # Strategy 3: JavaScript click
                                        page.evaluate(
                                            "arguments[0].click();", verify_button
                                        )
                                        print("JavaScript click successful")
                                    except Exception as e3:
                                        print(f"JavaScript click failed: {e3}")
                                        # Strategy 4: Try clicking the span inside the button
                                        try:
                                            span_element = verify_button.locator(
                                                "span"
                                            ).first
                                            if span_element.is_visible():
                                                span_element.click(force=True)
                                                print("Span click successful")
                                            else:
                                                raise Exception("Span not visible")
                                        except Exception as e4:
                                            print(f"All click strategies failed: {e4}")
                                            raise e4

                            # Wait for login to complete
                            page.wait_for_load_state("networkidle", timeout=100000)
                            time.sleep(3)  # Additional wait for any redirects

                            print("Login completed successfully!")

                            # Save the session state for future use
                            try:
                                context.storage_state(path="trailhead_session.json")
                                print(
                                    "✅ Session saved successfully! You won't need to log in again."
                                )
                            except Exception as e:
                                print(f"Warning: Could not save session: {e}")

                            return {
                                "browser_context": context,
                                "page": page,
                                "session_restored": False,
                            }
                        else:
                            print("Could not find verify button")
                    else:
                        print("Could not find verification code field")
                else:
                    print("Could not retrieve verification code from Gmail")
            else:
                print("Could not find submit button")
        else:
            print("Could not find username field")

        # If we get here, we couldn't complete the login process
        # but we still have the browser context and page available
        print("Login process could not be completed")
        return {"browser_context": context, "page": page, "session_restored": False}

    except Exception as e:
        print(f"Error during login process: {e}")
        # Return the context and page even if there was an error
        return {"browser_context": context, "page": page, "session_restored": False}
