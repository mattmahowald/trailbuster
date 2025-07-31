# TrailBuster - Salesforce Trailhead Automation

A Python automation tool for Salesforce Trailhead using Playwright for browser automation and Gmail API for verification code retrieval.

## Features

- Automated login to Salesforce Trailhead
- Two-step authentication with email and verification code
- Gmail integration for automatic verification code retrieval
- Browser automation using Playwright
- reCAPTCHA detection with manual intervention support

## Setup

### 1. Install Dependencies

```bash
pip install playwright python-dotenv google-api-python-client google-auth-httplib2 google-auth-oauthlib
python -m playwright install
```

### 2. Gmail API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials and save as `credentials.json` in the project root

### 3. Environment Variables

Create a `.env` file in the project root:

```env
SALESFORCE_EMAIL=your_email@example.com
```

### 4. First Run Setup

On first run, the Gmail API will open a browser window for authentication. Follow the prompts to authorize access to your Gmail account.

## Usage

### Basic Login

```python
from basic import login_to_trailhead
import os
import dotenv

dotenv.load_dotenv()
email = os.getenv("SALESFORCE_EMAIL")

# Start the login process
result = login_to_trailhead(email)

if result:
    browser_context = result["browser_context"]
    page = result["page"]
    # Continue with your automation...
```

### Test the Setup

```bash
python test_login.py
```

### Session Management

The script automatically saves your login session so you don't need to log in every time:

```bash
# Normal run (uses saved session if available)
python basic.py

# Force new login (ignores saved session)
python basic.py --no-session

# Clear saved session
python basic.py --clear-session

# Read module using existing session (fast)
python basic.py --read-module
```

**Benefits:**

- ✅ No need to solve reCAPTCHA repeatedly
- ✅ No need to wait for verification codes
- ✅ Faster subsequent runs
- ✅ Session persists across browser restarts
- ✅ Quick module reading with `--read-module`

## How It Works

1. **Email Entry**: The script navigates to the Trailhead login page and enters your email address
2. **reCAPTCHA Handling**: Detects reCAPTCHA challenges and prompts for manual intervention
3. **Verification Code Retrieval**: Uses the Gmail API to find the latest verification code email from Salesforce
4. **Code Entry**: Automatically enters the verification code into the login form
5. **Login Completion**: Submits the form to complete the login process

## Files

- `basic.py` - Main login automation logic
- `salesforce_code.py` - Gmail API integration for verification code retrieval
- `test_login.py` - Test script to verify setup
- `module_info.json` - Extracted module information (not in repo)
- `trailhead_session.json` - Saved browser session (not in repo)
- `credentials.json` - Gmail API credentials (not in repo)
- `.env` - Environment variables (not in repo)

## Troubleshooting

### Common Issues

1. **"SALESFORCE_EMAIL not found"**: Make sure your `.env` file exists and contains the correct email
2. **Gmail API errors**: Ensure `credentials.json` is in the project root and Gmail API is enabled
3. **Browser automation issues**: Make sure Playwright browsers are installed (`python -m playwright install`)

### Debug Mode

The browser runs in non-headless mode by default, so you can see what's happening. For production use, change `headless=False` to `headless=True` in `basic.py`.

### reCAPTCHA Handling

When a reCAPTCHA challenge appears, the script will:

1. Detect the reCAPTCHA presence
2. Pause execution and prompt you to solve it manually
3. Wait for you to press Enter after solving
4. Continue with the automation flow

## Security Notes

- Never commit `credentials.json` or `.env` files to version control
- The `.gitignore` file is configured to exclude these sensitive files
- Gmail API tokens are stored locally in `token.json`
