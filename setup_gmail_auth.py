"""
Gmail OAuth Setup Script
Run this once to authenticate and generate token.json
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def setup_gmail_auth():
    """Run OAuth flow and save token."""
    creds = None

    # Check if token.json exists
    if os.path.exists('token.json'):
        print("Loading existing token...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...")
            print("A browser window will open for authentication.")
            print("Please sign in with: mahabrizwan1@gmail.com")

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✓ Token saved to token.json")
    else:
        print("✓ Valid token already exists")

    print("\n=== Gmail OAuth Setup Complete ===")
    print("You can now use Gmail API in your application")
    print("Token file: token.json")
    print("Scopes granted:")
    for scope in SCOPES:
        print(f"  - {scope}")

if __name__ == '__main__':
    setup_gmail_auth()
