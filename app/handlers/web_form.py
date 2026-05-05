"""Web form intake handler."""

import os
import logging
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.db.connection import get_db_pool
from app.handlers.gmail import gmail_handler
from app.agent.customer_success_agent import get_agent

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
        disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

        if disable_db:
            logger.info(f"Demo mode: Processing web form from {form_data.email}")
            return {
                "status": "success",
                "channel": "web_form",
                "ticket_id": f"demo-{form_data.email.split('@')[0]}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "message": "Demo mode: Request received successfully",
                "agent_response": "Thank you for your inquiry. In demo mode, your request has been received but not saved to a database.",
                "demo_mode": True
            }

        try:
            logger.info(f"Processing web form submission from: {form_data.email}")

            # Get agent to process the inquiry and generate solution
            # Agent will create ticket, search KB, and send response
            agent = get_agent()
            agent_response = await agent.handle_customer_inquiry(
                customer_id=form_data.email,
                message=f"Subject: {form_data.subject}\n\nMessage: {form_data.message}",
                channel="web_form",
                customer_name=form_data.name
            )

            logger.info(f"Agent processed inquiry. Success: {agent_response.get('success')}")

            # Get ticket_id from agent response
            ticket_id = agent_response.get('ticket_id', 'N/A')

            # If agent failed, create ticket manually as fallback
            if not agent_response.get('success') or not ticket_id or ticket_id == 'N/A':
                logger.warning("Agent failed or didn't create ticket - creating manually")
                ticket_id = await self._create_ticket(form_data)

                # Send basic confirmation email
                await self._send_basic_confirmation(form_data, ticket_id)
            else:
                # Agent succeeded - email already sent via send_response tool
                logger.info(f"Agent successfully processed request. Ticket: {ticket_id}")

            return {
                "status": "success",
                "channel": "web_form",
                "ticket_id": ticket_id,
                "message": "Support request submitted and processed successfully",
                "agent_response": agent_response.get('response', 'Processing your request'),
                "tools_used": agent_response.get('tools_used', 0)
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

    async def _send_basic_confirmation(self, form_data: WebFormRequest, ticket_id: str) -> None:
        """
        Send basic confirmation email when agent fails.

        Args:
            form_data: Form data
            ticket_id: Generated ticket ID
        """
        try:
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

Thank you for contacting TechCorp Support. We have received your request.

Ticket ID: {ticket_id}
Category: {category_display}
Subject: {form_data.subject}

Our support team is reviewing your request and will respond shortly.

Best regards,
TechCorp Support Team

---
Your message:
{form_data.message}
"""
            )
            logger.info(f"Basic confirmation email sent to {form_data.email}")
        except Exception as e:
            logger.warning(f"Could not send confirmation email: {e}")


# Singleton instance
web_form_handler = WebFormHandler()
