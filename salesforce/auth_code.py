import os
import re
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope for reading emails
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_salesforce_auth_code() -> Optional[str]:
    """
    Retrieve the latest Salesforce verification code from Gmail.
    
    Returns:
        The 6-digit verification code if found, None otherwise
    """
    try:
        service = _get_gmail_service()
        if not service:
            return None
            
        # Search for verification code emails
        results = service.users().messages().list(
            userId="me", 
            q="subject:One-time verification code"
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            print("No verification code messages found")
            return None
            
        # Get the latest message
        latest_message = service.users().messages().get(
            userId="me", 
            id=messages[0]["id"]
        ).execute()
        
        # Extract verification code from message snippet
        text = latest_message.get("snippet", "")
        code_match = re.search(r"\b\d{6}\b", text)
        
        if code_match:
            verification_code = code_match.group()
            print(f"Found verification code: {verification_code}")
            return verification_code
        else:
            print("No 6-digit verification code found in message")
            return None
            
    except HttpError as error:
        print(f"Gmail API error: {error}")
        return None
    except Exception as error:
        print(f"Unexpected error: {error}")
        return None


def _get_gmail_service():
    """
    Get authenticated Gmail service instance.
    
    Returns:
        Gmail service instance or None if authentication fails
    """
    try:
        creds = None
        
        # Load existing token
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing Gmail credentials...")
                creds.refresh(Request())
            else:
                print("Getting new Gmail credentials...")
                if not os.path.exists("credentials.json"):
                    print("Error: credentials.json not found. Please set up Gmail API credentials.")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
                
        return build("gmail", "v1", credentials=creds)
        
    except Exception as error:
        print(f"Failed to authenticate with Gmail: {error}")
        return None