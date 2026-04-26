"""Seed knowledge base with sample entries and embeddings."""

import asyncio
import logging
import os
import sys
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.connection import init_db, close_db, get_db_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample knowledge base entries
KNOWLEDGE_BASE_ENTRIES = [
    {
        "title": "How to Reset Your Password",
        "content": """If you've forgotten your password, you can reset it easily:
1. Go to the login page
2. Click on 'Forgot Password' link
3. Enter your email address
4. Check your email for a reset link
5. Click the link and create a new password
6. Your password must be at least 8 characters with one uppercase, one lowercase, and one number.

If you don't receive the email within 5 minutes, check your spam folder.""",
        "category": "account",
        "tags": ["password", "login", "reset", "account access"]
    },
    {
        "title": "Login Issues and Troubleshooting",
        "content": """Having trouble logging in? Try these steps:
1. Verify your email address is correct
2. Check if Caps Lock is on
3. Clear your browser cache and cookies
4. Try a different browser or incognito mode
5. Reset your password if needed
6. Disable browser extensions that might interfere
7. Check if your account is locked (too many failed attempts)

If none of these work, contact support with your account email.""",
        "category": "account",
        "tags": ["login", "troubleshooting", "access", "authentication"]
    },
    {
        "title": "Understanding Your Bill and Charges",
        "content": """Your monthly bill includes:
- Base subscription fee (charged on the 1st of each month)
- Usage-based charges (API calls, storage, bandwidth)
- Add-on features (if enabled)
- Taxes and fees (based on your location)

You can view detailed billing breakdown in your account dashboard under Billing > Invoice History.
Payment methods accepted: Credit card, debit card, PayPal, bank transfer (for enterprise).

Billing cycle: Monthly, starting from your signup date.""",
        "category": "billing",
        "tags": ["billing", "payment", "invoice", "charges", "subscription"]
    },
    {
        "title": "How to Request a Refund",
        "content": """Refund Policy:
- 30-day money-back guarantee for new customers
- Refunds processed within 5-7 business days
- Partial refunds available for unused subscription time

To request a refund:
1. Log into your account
2. Go to Billing > Refund Request
3. Select the reason for refund
4. Submit the request
5. Our billing team will review within 24 hours

Note: Refunds are issued to the original payment method. Enterprise customers should contact their account manager.""",
        "category": "billing",
        "tags": ["refund", "billing", "payment", "cancellation", "money back"]
    },
    {
        "title": "Product Features Overview",
        "content": """Our platform offers:

Core Features:
- Real-time data synchronization
- Advanced analytics dashboard
- Custom reporting tools
- API access with rate limiting
- Multi-user collaboration
- Role-based access control

Premium Features:
- Priority support (24/7)
- Advanced security features
- Custom integrations
- Dedicated account manager
- SLA guarantees
- White-label options

All features are accessible from your dashboard. Check your plan to see which features are included.""",
        "category": "features",
        "tags": ["features", "product", "capabilities", "functionality"]
    },
    {
        "title": "Account Settings and Preferences",
        "content": """Manage your account settings:

Profile Settings:
- Update name, email, phone number
- Change password
- Set timezone and language preferences
- Upload profile picture

Notification Settings:
- Email notifications (daily digest, instant alerts)
- SMS notifications (optional)
- In-app notifications
- Webhook configurations

Privacy Settings:
- Data sharing preferences
- Cookie settings
- Two-factor authentication (2FA)
- Session management

Access Settings > Preferences from your dashboard to customize.""",
        "category": "account",
        "tags": ["settings", "preferences", "account", "configuration", "profile"]
    },
    {
        "title": "API Rate Limits and Usage",
        "content": """API Rate Limits by Plan:

Free Tier: 100 requests/hour
Basic: 1,000 requests/hour
Pro: 10,000 requests/hour
Enterprise: Custom limits

Rate limit headers:
- X-RateLimit-Limit: Total requests allowed
- X-RateLimit-Remaining: Requests remaining
- X-RateLimit-Reset: Time when limit resets

If you exceed your limit, you'll receive a 429 error. Upgrade your plan for higher limits or contact sales for custom quotas.

Monitor your usage in Dashboard > API > Usage Statistics.""",
        "category": "features",
        "tags": ["api", "rate limit", "usage", "quota", "technical"]
    },
    {
        "title": "Data Security and Privacy",
        "content": """We take security seriously:

Data Protection:
- End-to-end encryption for data in transit (TLS 1.3)
- AES-256 encryption for data at rest
- Regular security audits and penetration testing
- SOC 2 Type II certified
- GDPR and CCPA compliant

Your Rights:
- Request data export (JSON/CSV format)
- Request data deletion (within 30 days)
- Opt-out of marketing communications
- Access your data processing records

Security Features:
- Two-factor authentication (2FA)
- IP whitelisting (Enterprise)
- Audit logs
- Session timeout controls

Report security issues to security@example.com""",
        "category": "security",
        "tags": ["security", "privacy", "data protection", "compliance", "encryption"]
    },
    {
        "title": "Common Error Messages and Solutions",
        "content": """Troubleshooting common errors:

Error 401 - Unauthorized:
- Check your API key is valid
- Verify authentication headers
- Ensure your account is active

Error 403 - Forbidden:
- Check your plan includes this feature
- Verify you have the required permissions
- Contact admin to grant access

Error 404 - Not Found:
- Verify the resource ID is correct
- Check if the resource was deleted
- Ensure you're using the correct endpoint

Error 500 - Server Error:
- This is on our end, we're working on it
- Try again in a few minutes
- Check status.example.com for updates

Error 503 - Service Unavailable:
- Scheduled maintenance (check status page)
- Temporary overload (retry with backoff)""",
        "category": "troubleshooting",
        "tags": ["errors", "troubleshooting", "debugging", "technical support"]
    },
    {
        "title": "How to Upgrade or Downgrade Your Plan",
        "content": """Change your subscription plan:

To Upgrade:
1. Go to Billing > Plans
2. Select your desired plan
3. Review the changes and pricing
4. Confirm upgrade
5. Changes take effect immediately
6. Prorated charges applied to next bill

To Downgrade:
1. Go to Billing > Plans
2. Select lower tier plan
3. Review feature changes
4. Confirm downgrade
5. Changes take effect at next billing cycle
6. No refund for current period

Plan Comparison:
- Free: Basic features, limited usage
- Basic: $29/month, standard features
- Pro: $99/month, advanced features
- Enterprise: Custom pricing, all features + support

Contact sales@example.com for enterprise plans.""",
        "category": "billing",
        "tags": ["upgrade", "downgrade", "plan", "subscription", "pricing"]
    }
]


async def seed_knowledge_base():
    """Seed knowledge base with sample entries."""
    try:
        # Initialize database
        await init_db()
        db_pool = get_db_pool()

        # Try to load sentence-transformers model
        model = None
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence-transformers model")
        except ImportError:
            logger.warning("sentence-transformers not installed, skipping embeddings")

        # Clear existing entries
        await db_pool.execute("DELETE FROM knowledge_base")
        logger.info("Cleared existing knowledge base entries")

        # Insert entries
        for entry in KNOWLEDGE_BASE_ENTRIES:
            embedding = None
            if model:
                # Generate embedding
                embedding = model.encode(f"{entry['title']} {entry['content']}").tolist()

            await db_pool.execute(
                """
                INSERT INTO knowledge_base (title, content, category, tags, embedding, active)
                VALUES ($1, $2, $3, $4, $5, true)
                """,
                entry['title'],
                entry['content'],
                entry['category'],
                entry['tags'],
                embedding
            )

            logger.info(f"Inserted: {entry['title']}")

        # Get count
        count = await db_pool.fetchval("SELECT COUNT(*) FROM knowledge_base WHERE active = true")
        logger.info(f"✓ Successfully seeded {count} knowledge base entries")

        if model:
            logger.info("✓ All entries have embeddings for semantic search")
        else:
            logger.warning("⚠ Entries created without embeddings (text search only)")

    except Exception as e:
        logger.error(f"Error seeding knowledge base: {e}", exc_info=True)
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
