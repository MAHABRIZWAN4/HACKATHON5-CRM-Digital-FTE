"""Agent tools for Customer Success FTE."""

import logging
import uuid
import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from app.db.connection import get_db_pool
from app.agent.formatters import ResponseFormatter

logger = logging.getLogger(__name__)


def validate_uuid(ticket_id: str) -> None:
    """
    Validate that ticket_id is a valid UUID format.

    Args:
        ticket_id: The ticket ID to validate

    Raises:
        ValueError: If ticket_id is not a valid UUID
    """
    try:
        uuid.UUID(ticket_id)
    except (ValueError, AttributeError, TypeError):
        raise ValueError(
            f"Invalid ticket_id format: '{ticket_id}'. "
            f"Expected UUID format (e.g., '550e8400-e29b-41d4-a716-446655440000'). "
            f"You must use the EXACT ticket_id returned by create_ticket, not a placeholder."
        )


# Pydantic models for tool inputs
class SearchKnowledgeBaseInput(BaseModel):
    """Input for search_knowledge_base tool."""
    query: str = Field(..., description="Search query for knowledge base")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")


class CreateTicketInput(BaseModel):
    """Input for create_ticket tool."""
    customer_id: str = Field(..., description="Customer identifier (email or phone)")
    issue: str = Field(..., min_length=1, description="Description of the issue")
    priority: str = Field(..., description="Priority level: low, medium, high, urgent")
    channel: str = Field(..., description="Channel: gmail, whatsapp, web_form")


class GetCustomerHistoryInput(BaseModel):
    """Input for get_customer_history tool."""
    customer_id: str = Field(..., description="Customer identifier (email or phone)")


class EscalateToHumanInput(BaseModel):
    """Input for escalate_to_human tool."""
    ticket_id: str = Field(..., description="Ticket ID to escalate")
    reason: str = Field(..., description="Reason for escalation")
    urgency: str = Field(..., description="Urgency level: low, medium, high")


class SendResponseInput(BaseModel):
    """Input for send_response tool."""
    ticket_id: str = Field(..., description="Ticket ID")
    message: str = Field(..., min_length=1, description="Response message to send")
    channel: str = Field(..., description="Channel: gmail, whatsapp, web_form")


# Tool implementations
async def search_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant articles using full-text search.

    Args:
        query: Search query
        max_results: Maximum number of results (1-20)

    Returns:
        Dict with search results
    """
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        # Return demo knowledge base results
        demo_results = [
            {
                "id": "demo-kb-1",
                "title": "Getting Started Guide",
                "content": "Welcome to our platform! Here's how to get started with your account...",
                "category": "general",
                "relevance": 0.95
            },
            {
                "id": "demo-kb-2",
                "title": "Billing and Payments",
                "content": "Information about billing cycles, payment methods, and invoices...",
                "category": "billing",
                "relevance": 0.85
            }
        ]

        return {
            "success": True,
            "query": query,
            "results": demo_results[:max_results],
            "total_found": len(demo_results),
            "search_method": "demo",
            "demo_mode": True
        }

    try:
        logger.info(f"Searching knowledge base: {query}")

        # Validate input
        input_data = SearchKnowledgeBaseInput(query=query, max_results=max_results)

        db_pool = get_db_pool()
        results = []

        # Try PostgreSQL full-text search first
        try:
            rows = await db_pool.fetch(
                """
                SELECT id, title, content, category,
                       ts_rank(to_tsvector('english', content || ' ' || title), plainto_tsquery('english', $1)) as relevance
                FROM knowledge_base
                WHERE active = true
                  AND to_tsvector('english', content || ' ' || title) @@ plainto_tsquery('english', $1)
                ORDER BY relevance DESC
                LIMIT $2
                """,
                input_data.query,
                input_data.max_results
            )

            results = [
                {
                    "id": str(row['id']),
                    "title": row['title'],
                    "content": row['content'],
                    "category": row['category'],
                    "relevance": float(row['relevance'])
                }
                for row in rows
            ]

            logger.info(f"Full-text search found {len(results)} results")

        except Exception as e:
            logger.warning(f"Full-text search failed, falling back to ILIKE search: {e}")
            results = []

        # Fallback to ILIKE search if full-text search fails or returns no results
        if not results:
            rows = await db_pool.fetch(
                """
                SELECT id, title, content, category
                FROM knowledge_base
                WHERE active = true
                  AND (
                    title ILIKE $1
                    OR content ILIKE $1
                    OR category ILIKE $1
                  )
                ORDER BY
                  CASE
                    WHEN title ILIKE $1 THEN 1
                    WHEN content ILIKE $2 THEN 2
                    ELSE 3
                  END
                LIMIT $3
                """,
                f"%{input_data.query}%",
                f"%{input_data.query[:50]}%",
                input_data.max_results
            )

            results = [
                {
                    "id": str(row['id']),
                    "title": row['title'],
                    "content": row['content'],
                    "category": row['category'],
                    "relevance": 0.7
                }
                for row in rows
            ]

            logger.info(f"ILIKE search found {len(results)} results")

        return {
            "success": True,
            "query": input_data.query,
            "results": results,
            "total_found": len(results),
            "search_method": "fulltext" if results else "ilike"
        }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str,
    channel: str
) -> Dict[str, Any]:
    """
    Create a support ticket.

    Args:
        customer_id: Customer identifier
        issue: Issue description
        priority: Priority level (low, medium, high, urgent)
        channel: Channel (gmail, whatsapp, web_form)

    Returns:
        Dict with ticket details
    """
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        # Return demo ticket
        demo_ticket_id = f"demo-ticket-{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "ticket_id": demo_ticket_id,
            "customer_id": customer_id,
            "priority": priority,
            "channel": channel,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "demo_mode": True
        }

    try:
        logger.info(f"Creating ticket for customer: {customer_id}")

        # Validate input
        input_data = CreateTicketInput(
            customer_id=customer_id,
            issue=issue,
            priority=priority,
            channel=channel
        )

        # Validate priority
        valid_priorities = ["low", "medium", "high", "urgent"]
        if input_data.priority.lower() not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")

        # Validate channel
        valid_channels = ["gmail", "whatsapp", "web_form"]
        if input_data.channel.lower() not in valid_channels:
            raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")

        # Create ticket in database
        db_pool = get_db_pool()

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Check if customer exists
                customer_db_id = await conn.fetchval(
                    """
                    SELECT id FROM customers WHERE email = $1 OR phone = $1
                    """,
                    input_data.customer_id
                )

                # If customer doesn't exist, create one
                if not customer_db_id:
                    customer_db_id = await conn.fetchval(
                        """
                        INSERT INTO customers (email, name, created_at, updated_at)
                        VALUES ($1, $2, NOW(), NOW())
                        RETURNING id
                        """,
                        input_data.customer_id,
                        "Customer"  # Default name
                    )
                    logger.info(f"Created new customer: {customer_db_id}")

                # Map channel to database format
                channel_map = {
                    "gmail": "email",
                    "whatsapp": "whatsapp",
                    "web_form": "web"
                }
                db_channel = channel_map.get(input_data.channel.lower(), "web")

                # Create conversation
                conversation_id = await conn.fetchval(
                    """
                    INSERT INTO conversations (customer_id, channel, status, subject, created_at, updated_at)
                    VALUES ($1, $2, 'active', $3, NOW(), NOW())
                    RETURNING id
                    """,
                    customer_db_id,
                    db_channel,
                    input_data.issue[:100]  # Use first 100 chars as subject
                )
                logger.info(f"Created conversation: {conversation_id}")

                # Create ticket
                ticket_id = await conn.fetchval(
                    """
                    INSERT INTO tickets (conversation_id, customer_id, title, description, status, priority, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, 'open', $5, NOW(), NOW())
                    RETURNING id
                    """,
                    conversation_id,
                    customer_db_id,
                    input_data.issue[:200],  # Title
                    input_data.issue,  # Full description
                    input_data.priority.lower()
                )
                logger.info(f"Created ticket: {ticket_id}")

                # Create initial message
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, sender_type, sender_id, content, created_at)
                    VALUES ($1, 'customer', $2, $3, NOW())
                    """,
                    conversation_id,
                    input_data.customer_id,
                    input_data.issue
                )

        logger.info(f"Ticket created successfully: {ticket_id}")

        return {
            "success": True,
            "ticket_id": str(ticket_id),
            "customer_id": input_data.customer_id,
            "priority": input_data.priority,
            "channel": input_data.channel,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating ticket: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def get_customer_history(customer_id: str) -> Dict[str, Any]:
    """
    Get customer's support history.

    Args:
        customer_id: Customer identifier

    Returns:
        Dict with customer history
    """
    try:
        logger.info(f"Fetching customer history: {customer_id}")

        # Validate input
        input_data = GetCustomerHistoryInput(customer_id=customer_id)

        # TODO: Implement actual database query
        # For now, return mock data
        history = {
            "customer_id": input_data.customer_id,
            "total_tickets": 3,
            "open_tickets": 1,
            "closed_tickets": 2,
            "recent_tickets": [
                {
                    "ticket_id": "ticket_001",
                    "issue": "Login problem",
                    "status": "closed",
                    "created_at": "2026-04-01T10:00:00Z"
                },
                {
                    "ticket_id": "ticket_002",
                    "issue": "Feature request",
                    "status": "closed",
                    "created_at": "2026-04-03T14:30:00Z"
                }
            ],
            "customer_since": "2025-01-15",
            "satisfaction_score": 4.5
        }

        return {
            "success": True,
            "history": history
        }

    except Exception as e:
        logger.error(f"Error fetching customer history: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "history": None
        }


async def escalate_to_human(
    ticket_id: str,
    reason: str,
    urgency: str
) -> Dict[str, Any]:
    """
    Escalate ticket to human agent.

    Args:
        ticket_id: Ticket ID to escalate
        reason: Reason for escalation
        urgency: Urgency level (low, medium, high)

    Returns:
        Dict with escalation details
    """
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        logger.info(f"Demo mode: Escalating ticket {ticket_id}")
        return {
            "success": True,
            "ticket_id": ticket_id,
            "escalated": True,
            "reason": reason,
            "urgency": urgency,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Demo mode: Ticket escalation recorded (not saved to database)",
            "demo_mode": True
        }

    try:
        logger.info(f"Escalating ticket {ticket_id}: {reason}")

        # Validate UUID format before database call
        validate_uuid(ticket_id)

        # Validate input
        input_data = EscalateToHumanInput(
            ticket_id=ticket_id,
            reason=reason,
            urgency=urgency
        )

        # Validate urgency
        valid_urgencies = ["low", "medium", "high"]
        if input_data.urgency.lower() not in valid_urgencies:
            raise ValueError(f"Invalid urgency. Must be one of: {valid_urgencies}")

        # Update ticket in database
        db_pool = get_db_pool()

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # Get customer email for notification
                ticket_data = await conn.fetchrow(
                    """
                    SELECT t.id, t.title, c.email, c.name
                    FROM tickets t
                    JOIN customers c ON t.customer_id = c.id
                    WHERE t.id = $1::uuid
                    """,
                    ticket_id
                )

                if not ticket_data:
                    raise ValueError(f"Ticket {ticket_id} not found")

                # Update ticket with escalation data
                escalation_metadata = json.dumps({
                    "escalation_reason": input_data.reason,
                    "escalation_urgency": input_data.urgency
                })

                await conn.execute(
                    """
                    UPDATE tickets
                    SET escalated = true,
                        escalated_at = NOW(),
                        status = 'escalated',
                        metadata = metadata || $2::jsonb
                    WHERE id = $1::uuid
                    """,
                    ticket_id,
                    escalation_metadata
                )

                logger.info(f"Ticket {ticket_id} marked as escalated in database")

        # Send email notification to support team
        support_email = os.getenv("SUPPORT_EMAIL")

        if support_email:
            from app.handlers.gmail import gmail_handler

            try:
                email_body = f"""New escalation requires attention!

Customer: {ticket_data['email']} ({ticket_data['name']})
Ticket ID: {ticket_id}
Reason: {input_data.reason}
Urgency: {input_data.urgency.upper()}

Login to dashboard to handle this case.
"""

                await gmail_handler.send_reply(
                    to_email=support_email,
                    subject=f"🚨 ESCALATION: {input_data.reason} - Ticket {ticket_id}",
                    body=email_body
                )
                logger.info(f"Escalation email sent to {support_email}")
            except Exception as e:
                logger.warning(f"Failed to send escalation email: {e}")

        return {
            "success": True,
            "ticket_id": input_data.ticket_id,
            "escalated": True,
            "reason": input_data.reason,
            "urgency": input_data.urgency,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Ticket has been escalated to a human agent. They will respond shortly."
        }

    except Exception as e:
        logger.error(f"Error escalating ticket: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "escalated": False
        }


async def send_response(
    ticket_id: str,
    message: str,
    channel: str
) -> Dict[str, Any]:
    """
    Send response to customer via appropriate channel.

    Args:
        ticket_id: Ticket ID
        message: Response message
        channel: Channel (gmail, whatsapp, web_form)

    Returns:
        Dict with send status
    """
    disable_db = os.getenv("DISABLE_DB", "false").lower() == "true"

    if disable_db:
        logger.info(f"Demo mode: Sending response for ticket {ticket_id}")
        formatted_message = ResponseFormatter.format_response(message, channel)
        return {
            "success": True,
            "ticket_id": ticket_id,
            "channel": channel,
            "message_sent": True,
            "formatted_message": formatted_message,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "recipient": "demo@example.com",
            "demo_mode": True
        }

    try:
        logger.info(f"Sending response for ticket {ticket_id} via {channel}")

        # Validate UUID format before database call
        validate_uuid(ticket_id)

        # Validate input
        input_data = SendResponseInput(
            ticket_id=ticket_id,
            message=message,
            channel=channel
        )

        # Validate channel
        valid_channels = ["gmail", "whatsapp", "web_form"]
        if input_data.channel.lower() not in valid_channels:
            raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")

        # Format message for channel
        formatted_message = ResponseFormatter.format_response(
            input_data.message,
            input_data.channel
        )

        # Get customer email from ticket
        db_pool = get_db_pool()
        customer_data = await db_pool.fetchrow(
            """
            SELECT c.email, c.name, t.title
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.id = $1::uuid
            """,
            ticket_id
        )

        if not customer_data:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Send via appropriate channel
        if input_data.channel.lower() in ["gmail", "web_form"]:
            # Import here to avoid circular dependency
            from app.handlers.gmail import gmail_handler

            try:
                await gmail_handler.send_reply(
                    to_email=customer_data['email'],
                    subject=f"Re: {customer_data['title']}",
                    body=formatted_message
                )
                logger.info(f"Email sent to {customer_data['email']}")
            except ValueError as e:
                logger.warning(f"Gmail not configured: {e}")
                # Continue even if email fails
        elif input_data.channel.lower() == "whatsapp":
            # Import here to avoid circular dependency
            from app.handlers.whatsapp import whatsapp_handler

            try:
                # Get customer phone from database
                customer_phone = await db_pool.fetchval(
                    """
                    SELECT phone FROM customers c
                    JOIN tickets t ON t.customer_id = c.id
                    WHERE t.id = $1::uuid
                    """,
                    ticket_id
                )

                if customer_phone:
                    await whatsapp_handler.send_message(
                        to_number=customer_phone,
                        body=formatted_message
                    )
                    logger.info(f"WhatsApp message sent to {customer_phone}")
                else:
                    logger.warning(f"No phone number found for ticket {ticket_id}")
            except Exception as e:
                logger.error(f"Failed to send WhatsApp message: {e}")
                # Continue even if WhatsApp fails

        # Store response in database
        await db_pool.execute(
            """
            INSERT INTO messages (conversation_id, sender_type, sender_id, content, created_at)
            SELECT conversation_id, 'agent', 'customer_success_agent', $2, NOW()
            FROM tickets WHERE id = $1::uuid
            """,
            ticket_id,
            formatted_message
        )

        logger.info(f"Response sent successfully for ticket {ticket_id}")

        return {
            "success": True,
            "ticket_id": input_data.ticket_id,
            "channel": input_data.channel,
            "message_sent": True,
            "formatted_message": formatted_message,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "recipient": customer_data['email']
        }

    except Exception as e:
        logger.error(f"Error sending response: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message_sent": False
        }
