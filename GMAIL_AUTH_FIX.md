# Gmail OAuth Access Blocked - Fix

## Problem
Error 403: access_denied - "Hackathon CRM has not completed the Google verification process"

## Solution: Add Test User

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Select your project** (the one with OAuth credentials)

3. **Navigate to OAuth consent screen:**
   - Left menu → APIs & Services → OAuth consent screen

4. **Add Test Users:**
   - Scroll down to "Test users" section
   - Click "ADD USERS"
   - Enter: mahabrizwan1@gmail.com
   - Click "SAVE"

5. **Run setup again:**
   ```bash
   python setup_gmail_auth.py
   ```

## Alternative Solutions

### Option 2: Publish the App (Not Recommended for Testing)
- In OAuth consent screen, click "PUBLISH APP"
- This makes it public but requires Google verification for sensitive scopes

### Option 3: Use Different Credentials
- Create new OAuth credentials with the correct test user already added

## Notes
- Testing mode allows up to 100 test users
- No verification needed for testing mode
- Your app can stay in testing mode indefinitely for development
