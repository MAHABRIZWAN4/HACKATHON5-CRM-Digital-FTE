"""WhatsApp (Twilio) intake handler."""

import logging
import os
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)


class TwilioConfig:
    """Twilio configuration."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.webhook_url = os.getenv("TWILIO_WEBHOOK_URL", "")

    def validate(self) -> None:
        """Validate Twilio configuration."""
        if not self.account_sid:
            raise ValueError("TWILIO_ACCOUNT_SID is required")
        if not self.auth_token:
            raise ValueError("TWILIO_AUTH_TOKEN is required")
        if not self.phone_number:
            raise ValueError("TWILIO_PHONE_NUMBER is required")


class WhatsAppMessage:
    """Parsed WhatsApp message."""

    def __init__(
        self,
        message_sid: str,
        from_number: str,
        to_number: str,
        body: str,
        timestamp: datetime,
        media_urls: Optional[list] = None
    ):
        self.message_sid = message_sid
        self.from_number = from_number
        self.to_number = to_number
        self.body = body
        self.timestamp = timestamp
        self.media_urls = media_urls or []


class WhatsAppHandler:
    """Handler for WhatsApp (Twilio) webhook events."""

    def __init__(self):
        self.config = TwilioConfig()

    def validate_signature(
        self,
        signature: str,
        url: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        Validate Twilio webhook signature.

        Args:
            signature: X-Twilio-Signature header value
            url: Full webhook URL
            params: POST parameters

        Returns:
            True if signature is valid
        """
        try:
            # Construct the data string
            data = url
            for key in sorted(params.keys()):
                data += f"{key}{params[key]}"

            # Compute HMAC-SHA1
            expected_signature = hmac.new(
                self.config.auth_token.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha1
            ).digest()

            # Base64 encode
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode()

            # Compare signatures
            return hmac.compare_digest(signature, expected_signature_b64)

        except Exception as e:
            logger.error(f"Error validating Twilio signature: {e}", exc_info=True)
            return False

    async def process_webhook(
        self,
        webhook_data: Dict[str, Any],
        signature: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process WhatsApp webhook event.

        Args:
            webhook_data: Webhook payload from Twilio
            signature: X-Twilio-Signature header (optional for testing)
            url: Webhook URL (optional for testing)

        Returns:
            Dict with status and ticket_id
        """
        try:
            logger.info(f"Processing WhatsApp webhook: {webhook_data}")

            # Validate signature if provided
            if signature and url:
                if not self.validate_signature(signature, url, webhook_data):
                    logger.warning("Invalid Twilio signature")
                    raise ValueError("Invalid webhook signature")

            # Parse the message
            message = self._parse_message(webhook_data)

            # Create ticket in database
            ticket_id = await self._create_ticket(message)

            # TODO: Send auto-reply
            # await self._send_reply(message.from_number, f"Ticket created: {ticket_id}")

            logger.info(f"WhatsApp webhook processed successfully. Ticket ID: {ticket_id}")

            return {
                "status": "success",
                "channel": "whatsapp",
                "ticket_id": ticket_id,
                "message": "WhatsApp message processed successfully"
            }

        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {e}", exc_info=True)
            raise

    def _parse_message(self, webhook_data: Dict[str, Any]) -> WhatsAppMessage:
        """
        Parse Twilio webhook data into structured message.

        Args:
            webhook_data: Raw webhook data from Twilio

        Returns:
            Parsed WhatsAppMessage
        """
        # Extract message details from Twilio webhook
        message_sid = webhook_data.get("MessageSid", "unknown")
        from_number = webhook_data.get("From", "")
        to_number = webhook_data.get("To", "")
        body = webhook_data.get("Body", "")

        # Extract media URLs if present
        num_media = int(webhook_data.get("NumMedia", 0))
        media_urls = []
        for i in range(num_media):
            media_url = webhook_data.get(f"MediaUrl{i}")
            if media_url:
                media_urls.append(media_url)

        return WhatsAppMessage(
            message_sid=message_sid,
            from_number=from_number,
            to_number=to_number,
            body=body,
            timestamp=datetime.now(timezone.utc),
            media_urls=media_urls
        )

    async def _create_ticket(self, message: WhatsAppMessage) -> str:
        """
        Create ticket from WhatsApp message.

        Args:
            message: Parsed WhatsApp message

        Returns:
            Ticket ID
        """
        db_pool = get_db_pool()

        logger.info("Starting WhatsApp ticket creation transaction")

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Extract phone number from WhatsApp format (whatsapp:+1234567890)
                phone_number = message.from_number.replace('whatsapp:', '')
                # Use phone as email placeholder
                customer_email = f"{phone_number.replace('+', '').replace(' ', '')}@whatsapp.user"

                # Check if customer exists by phone/email
                customer_id = await conn.fetchval(
                    """
                    SELECT id FROM customers WHERE email = $1 OR phone = $2
                    """,
                    customer_email,
                    phone_number
                )

                # Create customer if doesn't exist
                if not customer_id:
                    customer_id = await conn.fetchval(
                        """
                        INSERT INTO customers (name, email, phone, created_at, updated_at)
                        VALUES ($1, $2, $3, NOW(), NOW())
                        RETURNING id
                        """,
                        f"WhatsApp User {phone_number}",
                        customer_email,
                        phone_number
                    )
                    logger.info(f"Created new customer: {customer_id}")
                else:
                    # Update existing customer
                    await conn.execute(
                        """
                        UPDATE customers SET updated_at = NOW()
                        WHERE id = $1
                        """,
                        customer_id
                    )
                    logger.info(f"Updated existing customer: {customer_id}")

                # Create conversation
                subject = message.body[:100] if message.body else "WhatsApp Message"
                conversation_id = await conn.fetchval(
                    """
                    INSERT INTO conversations (customer_id, channel, status, subject, created_at, updated_at)
                    VALUES ($1, 'whatsapp', 'active', $2, NOW(), NOW())
                    RETURNING id
                    """,
                    customer_id,
                    subject
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
                    subject,
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
                    phone_number,
                    message.body
                )
                logger.info("Created message")

                logger.info("Transaction committed successfully")
                return str(ticket_id)

    async def send_message(self, to_number: str, body: str) -> bool:
        """
        Send WhatsApp message via Twilio API.

        Args:
            to_number: Recipient phone number (WhatsApp format)
            body: Message body

        Returns:
            True if sent successfully
        """
        try:
            self.config.validate()

            # TODO: Implement Twilio API sending
            logger.info(f"Would send WhatsApp message to {to_number}: {body}")

            return True

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return False


# Singleton instance
whatsapp_handler = WhatsAppHandler()
