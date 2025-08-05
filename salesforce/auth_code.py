"""
Gmail API integration for retrieving Salesforce verification codes.

This module provides clean Gmail API integration to automatically retrieve
verification codes sent to Gmail during the Salesforce Trailhead login process.
"""

import os
import re
import time
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from trailbuster.logger import get_logger, log_gmail, log_performance

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Gmail API service
gmail_service = None


def get_salesforce_auth_code(max_attempts: int = 10, delay: int = 5) -> Optional[str]:
    """
    Retrieve Salesforce verification code from Gmail.

    Args:
        max_attempts: Maximum number of attempts to find the code
        delay: Delay between attempts in seconds

    Returns:
        Verification code if found, None otherwise
    """
    logger = get_logger("GMAIL")
    logger.start_operation(
        "verification_code_retrieval", max_attempts=max_attempts, delay=delay
    )

    start_time = time.time()

    try:
        # Initialize Gmail service
        service = _get_gmail_service()
        if not service:
            logger.error("Failed to initialize Gmail service")
            logger.end_operation(
                "verification_code_retrieval",
                success=False,
                error="Gmail service initialization failed",
            )
            return None

        # Search for verification code messages
        for attempt in range(max_attempts):
            logger.info(
                f"Attempt {attempt + 1}/{max_attempts} to find verification code"
            )

            try:
                # Search for recent messages from Salesforce
                query = "from:salesforce.com subject:verification newer_than:1d"
                results = (
                    service.users().messages().list(userId="me", q=query).execute()
                )

                messages = results.get("messages", [])

                if not messages:
                    logger.info("No verification code messages found")
                    if attempt < max_attempts - 1:
                        logger.info(f"Waiting {delay} seconds before next attempt...")
                        time.sleep(delay)
                    continue

                # Check each message for verification code
                for message in messages[:5]:  # Check most recent 5 messages
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=message["id"])
                        .execute()
                    )

                    # Extract message body
                    body = _extract_message_body(msg)
                    if not body:
                        continue

                    # Look for verification code pattern
                    verification_code = _extract_verification_code(body)
                    if verification_code:
                        duration = time.time() - start_time
                        log_performance(
                            "verification_code_retrieval", duration, attempt=attempt + 1
                        )

                        logger.info(f"Found verification code: {verification_code}")
                        logger.end_operation(
                            "verification_code_retrieval",
                            success=True,
                            code=verification_code,
                        )
                        return verification_code

                # If no code found in recent messages, wait and try again
                if attempt < max_attempts - 1:
                    logger.info(f"Waiting {delay} seconds before next attempt...")
                    time.sleep(delay)

            except Exception as e:
                logger.warning(f"Error during attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(delay)

        logger.warning("No 6-digit verification code found in message")
        logger.end_operation(
            "verification_code_retrieval",
            success=False,
            error="No verification code found",
        )
        return None

    except Exception as e:
        logger.error(f"Gmail API error: {e}")
        logger.end_operation("verification_code_retrieval", success=False, error=str(e))
        return None


def _get_gmail_service():
    """Initialize and return Gmail API service."""
    global gmail_service

    if gmail_service:
        return gmail_service

    logger = get_logger("GMAIL")

    try:
        creds = None

        # Check if token file exists
        if os.path.exists("token.json"):
            logger.info("Loading existing Gmail credentials...")
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # If no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail credentials...")
                creds.refresh(Request())
            else:
                logger.info("Getting new Gmail credentials...")
                logger.info(
                    "Please authenticate with your Gmail account to enable verification code retrieval"
                )

                if not os.path.exists("credentials.json"):
                    logger.error(
                        "credentials.json file not found. Please download it from Google Cloud Console"
                    )
                    return None

                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        # Build the Gmail service
        gmail_service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service initialized successfully")
        return gmail_service

    except Exception as e:
        logger.error(f"Failed to authenticate with Gmail: {e}")
        return None


def _extract_message_body(message):
    """Extract the body text from a Gmail message."""
    try:
        # Get message payload
        payload = message.get("payload", {})

        # Handle multipart messages
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        import base64

                        return base64.urlsafe_b64decode(data).decode("utf-8")

        # Handle simple text messages
        elif payload.get("mimeType") == "text/plain":
            data = payload["body"].get("data", "")
            if data:
                import base64

                return base64.urlsafe_b64decode(data).decode("utf-8")

        return None

    except Exception as e:
        logger = get_logger("GMAIL")
        logger.debug(f"Error extracting message body: {e}")
        return None


def _extract_verification_code(text: str) -> Optional[str]:
    """Extract 6-digit verification code from text."""
    try:
        # Look for 6-digit patterns
        patterns = [
            r"\b\d{6}\b",  # Standalone 6 digits
            r"verification code[:\s]*(\d{6})",  # "verification code: 123456"
            r"code[:\s]*(\d{6})",  # "code: 123456"
            r"(\d{6})",  # Any 6 digits
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first match (or the group if it's a group match)
                code = matches[0] if isinstance(matches[0], str) else matches[0][0]
                if code.isdigit() and len(code) == 6:
                    return code

        return None

    except Exception as e:
        logger = get_logger("GMAIL")
        logger.debug(f"Error extracting verification code: {e}")
        return None
