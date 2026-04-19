"""Gmail intake handler with real Gmail API integration."""

import logging
import os
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)


class GmailConfig:
    """Gmail API configuration."""

    def __init__(self):
        # Use absolute paths relative to project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", os.path.join(project_root, "credentials.json"))
        self.token_file = os.getenv("GMAIL_TOKEN_FILE", os.path.join(project_root, "token.json"))
        self.gmail_address = os.getenv("GMAIL_ADDRESS", "")

    def validate(self) -> None:
        """Validate Gmail configuration."""
        if not self.gmail_address:
            raise ValueError("GMAIL_ADDRESS is required in .env")
        if not os.path.exists(self.credentials_file):
            raise ValueError(f"Credentials file not found: {self.credentials_file}")
        if not os.path.exists(self.token_file):
            raise ValueError(f"Token file not found: {self.token_file}. Run setup_gmail_auth.py first")


class GmailMessage:
    """Parsed Gmail message."""

    def __init__(
        self,
        message_id: str,
        from_email: str,
        from_name: Optional[str],
        subject: str,
        body: str,
        timestamp: datetime
    ):
        self.message_id = message_id
        self.from_email = from_email
        self.from_name = from_name
        self.subject = subject
        self.body = body
        self.timestamp = timestamp


class GmailHandler:
    """Handler for Gmail webhook events with real Gmail API integration."""

    def __init__(self):
        self.config = GmailConfig()
        self._service = None

    def _get_gmail_service(self):
        """Get authenticated Gmail API service."""
        if self._service:
            return self._service

        try:
            self.config.validate()

            # Load credentials from token.json
            creds = Credentials.from_authorized_user_file(
                self.config.token_file,
                ['https://www.googleapis.com/auth/gmail.readonly',
                 'https://www.googleapis.com/auth/gmail.send']
            )

            # Build Gmail service
            self._service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized successfully")
            return self._service

        except Exception as e:
            logger.error(f"Error initializing Gmail service: {e}")
            raise

    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Gmail webhook event.

        Args:
            webhook_data: Webhook payload from Gmail

        Returns:
            Dict with status and ticket_id
        """
        try:
            logger.info(f"Processing Gmail webhook: {webhook_data}")

            # Parse the email message
            message = self._parse_message(webhook_data)

            # Create ticket in database
            ticket_id = await self._create_ticket(message)

            # Send auto-reply
            await self.send_reply(
                to_email=message.from_email,
                subject=f"Re: {message.subject}",
                body=f"""Hello {message.from_name or 'there'},

Thank you for contacting us. We have received your message and created a support ticket.

Ticket ID: {ticket_id}

Our AI-powered support team is reviewing your request and will respond shortly. We typically reply within 2 minutes.

Best regards,
TechCorp Support Team

---
Original message:
{message.body[:200]}{'...' if len(message.body) > 200 else ''}
"""
            )

            logger.info(f"Gmail webhook processed successfully. Ticket ID: {ticket_id}")

            return {
                "status": "success",
                "channel": "gmail",
                "ticket_id": ticket_id,
                "message": "Email processed successfully"
            }

        except Exception as e:
            logger.error(f"Error processing Gmail webhook: {e}", exc_info=True)
            raise

    def _parse_message(self, webhook_data: Dict[str, Any]) -> GmailMessage:
        """
        Parse Gmail webhook data into structured message.

        Args:
            webhook_data: Raw webhook data

        Returns:
            Parsed GmailMessage
        """
        # Extract message details from webhook
        message_id = webhook_data.get("message_id", "unknown")
        from_email = webhook_data.get("from", "unknown@example.com")
        from_name = webhook_data.get("from_name")
        subject = webhook_data.get("subject", "No Subject")
        body = webhook_data.get("body", "")
        timestamp = datetime.now(timezone.utc)

        return GmailMessage(
            message_id=message_id,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body=body,
            timestamp=timestamp
        )

    async def _create_ticket(self, message: GmailMessage) -> str:
        """
        Create ticket from Gmail message.

        Args:
            message: Parsed Gmail message

        Returns:
            Ticket ID
        """
        db_pool = get_db_pool()

        logger.info("Starting Gmail ticket creation transaction")

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Check if customer exists by email
                customer_id = await conn.fetchval(
                    """
                    SELECT id FROM customers WHERE email = $1
                    """,
                    message.from_email
                )

                # Create customer if doesn't exist
                if not customer_id:
                    customer_name = message.from_name or message.from_email.split('@')[0]
                    customer_id = await conn.fetchval(
                        """
                        INSERT INTO customers (name, email, created_at, updated_at)
                        VALUES ($1, $2, NOW(), NOW())
                        RETURNING id
                        """,
                        customer_name,
                        message.from_email
                    )
                    logger.info(f"Created new customer: {customer_id}")
                else:
                    # Update existing customer
                    if message.from_name:
                        await conn.execute(
                            """
                            UPDATE customers SET name = $1, updated_at = NOW()
                            WHERE id = $2
                            """,
                            message.from_name,
                            customer_id
                        )
                    logger.info(f"Updated existing customer: {customer_id}")

                # Create conversation
                conversation_id = await conn.fetchval(
                    """
                    INSERT INTO conversations (customer_id, channel, status, subject, created_at, updated_at)
                    VALUES ($1, 'gmail', 'active', $2, NOW(), NOW())
                    RETURNING id
                    """,
                    customer_id,
                    message.subject
                )
                logger.info(f"Created conversation: {conversation_id}")

                # Create ticket
                ticket_id = await conn.fetchval(
                    """
                    INSERT INTO tickets (conversation_id, customer_id, title, description, status, priority, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, 'open', 'medium', NOW(), NOW())
                    RETURNING id
                    """,
                    conversation_id,
                    customer_id,
                    message.subject,
                    message.body
                )
                logger.info(f"Created ticket: {ticket_id}")

                # Create message
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, sender_type, sender_id, content, created_at)
                    VALUES ($1, 'customer', $2, $3, NOW())
                    """,
                    conversation_id,
                    message.from_email,
                    message.body
                )
                logger.info("Created message")

                logger.info("Transaction committed successfully")
                return str(ticket_id)

    async def send_reply(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send reply email via Gmail API.

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body

        Returns:
            True if sent successfully
        """
        try:
            self.config.validate()
            service = self._get_gmail_service()

            # Create MIME message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = self.config.gmail_address
            message['subject'] = subject

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send via Gmail API
            send_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Gmail reply sent successfully to {to_email}. Message ID: {send_message['id']}")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error sending reply: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending Gmail reply: {e}", exc_info=True)
            return False


# Singleton instance
gmail_handler = GmailHandler()
