"""Web form intake handler."""

import logging
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.db.connection import get_db_pool
from app.handlers.gmail import gmail_handler

logger = logging.getLogger(__name__)


class WebFormRequest(BaseModel):
    """Web form request model."""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=5000)
    category: str = Field(default="general", max_length=100)


class WebFormHandler:
    """Handler for web form submissions."""

    async def process_submission(self, form_data: WebFormRequest) -> Dict[str, Any]:
        """
        Process web form submission.

        Args:
            form_data: Validated form data

        Returns:
            Dict with status, ticket_id, and message
        """
        try:
            logger.info(f"Processing web form submission from: {form_data.email}")

            # Create ticket in database
            ticket_id = await self._create_ticket(form_data)

            # Send confirmation email
            await self._send_confirmation_email(form_data, ticket_id)

            logger.info(f"Web form submission processed successfully. Ticket ID: {ticket_id}")

            return {
                "status": "success",
                "channel": "web_form",
                "ticket_id": ticket_id,
                "message": "Support request submitted successfully"
            }

        except Exception as e:
            logger.error(f"Error processing web form submission: {e}", exc_info=True)
            raise

    async def _create_ticket(self, form_data: WebFormRequest) -> str:
        """
        Create ticket in database.

        Args:
            form_data: Form data

        Returns:
            Ticket ID
        """
        db_pool = get_db_pool()

        logger.info("Starting ticket creation transaction")

        # Use a transaction to ensure all operations commit together
        async with db_pool.acquire() as conn:
            logger.info("Acquired database connection")
            async with conn.transaction():
                logger.info("Started transaction")

                # Check if customer exists by email
                customer_id = await conn.fetchval(
                    """
                    SELECT id FROM customers WHERE email = $1
                    """,
                    form_data.email
                )
                logger.info(f"Customer lookup result: {customer_id}")

                # Create customer if doesn't exist
                if not customer_id:
                    customer_id = await conn.fetchval(
                        """
                        INSERT INTO customers (name, email, created_at, updated_at)
                        VALUES ($1, $2, NOW(), NOW())
                        RETURNING id
                        """,
                        form_data.name,
                        form_data.email
                    )
                    logger.info(f"Created new customer: {customer_id}")
                else:
                    # Update existing customer
                    await conn.execute(
                        """
                        UPDATE customers SET name = $1, updated_at = NOW()
                        WHERE id = $2
                        """,
                        form_data.name,
                        customer_id
                    )
                    logger.info(f"Updated existing customer: {customer_id}")

                # Create conversation
                conversation_id = await conn.fetchval(
                    """
                    INSERT INTO conversations (customer_id, channel, status, subject, created_at, updated_at)
                    VALUES ($1, 'web', 'active', $2, NOW(), NOW())
                    RETURNING id
                    """,
                    customer_id,
                    form_data.subject
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
                    form_data.subject,
                    form_data.message
                )
                logger.info(f"Created ticket: {ticket_id}")

                # Create message
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, sender_type, sender_id, content, created_at)
                    VALUES ($1, 'customer', $2, $3, NOW())
                    """,
                    conversation_id,
                    form_data.email,
                    form_data.message
                )
                logger.info("Created message")

                logger.info("Transaction about to commit")

                # Transaction will auto-commit when exiting this block

            logger.info("Transaction committed successfully")
            return str(ticket_id)

    async def _send_confirmation_email(self, form_data: WebFormRequest, ticket_id: str) -> None:
        """
        Send confirmation email to customer.

        Args:
            form_data: Form data
            ticket_id: Generated ticket ID
        """
        try:
            # Map category to readable name
            category_names = {
                "general": "General Inquiry",
                "technical": "Technical Support",
                "billing": "Billing Issue",
                "feature": "Feature Request",
                "bug": "Bug Report"
            }
            category_display = category_names.get(form_data.category, form_data.category.title())

            await gmail_handler.send_reply(
                to_email=form_data.email,
                subject=f"Re: {form_data.subject}",
                body=f"""Hello {form_data.name},

Thank you for contacting us. We have received your support request and created a ticket.

Ticket ID: {ticket_id}
Category: {category_display}
Subject: {form_data.subject}

Our support team is reviewing your request and will respond shortly. We typically reply within 24 hours.

Best regards,
TechCorp Support Team

---
Your message:
{form_data.message[:200]}{'...' if len(form_data.message) > 200 else ''}
"""
            )
            logger.info(f"Confirmation email sent to {form_data.email}")
        except Exception as e:
            logger.error(f"Error sending confirmation email: {e}", exc_info=True)


# Singleton instance
web_form_handler = WebFormHandler()
