"""Ticket lifecycle management."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)


class TicketManager:
    """Manage ticket lifecycle and status transitions."""

    # Valid status transitions
    VALID_TRANSITIONS = {
        "open": ["processing", "escalated", "resolved", "closed"],
        "processing": ["resolved", "escalated", "closed"],
        "escalated": ["resolved", "closed"],
        "resolved": ["closed"],
        "closed": []
    }

    @staticmethod
    async def create_ticket(
        customer_id: str,
        issue: str,
        priority: str,
        channel: str,
        customer_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new support ticket.

        Args:
            customer_id: Customer identifier (email or phone)
            issue: Issue description
            priority: Priority level (low, medium, high, urgent)
            channel: Channel (gmail, whatsapp, web_form)
            customer_name: Optional customer name
            metadata: Optional additional metadata

        Returns:
            Dict with ticket details
        """
        try:
            logger.info(f"Creating ticket for customer: {customer_id}")

            # Validate priority
            valid_priorities = ["low", "medium", "high", "urgent"]
            if priority.lower() not in valid_priorities:
                raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")

            # Validate channel
            valid_channels = ["gmail", "whatsapp", "web_form"]
            if channel.lower() not in valid_channels:
                raise ValueError(f"Invalid channel. Must be one of: {valid_channels}")

            ticket_id = f"ticket_{uuid4().hex[:12]}"
            created_at = datetime.now(timezone.utc)

            # Store ticket in database (mock for now - would need actual table)
            db_pool = get_db_pool()

            # For now, just verify database connection
            await db_pool.fetchval("SELECT 1")

            logger.info(f"Created ticket: {ticket_id}")

            return {
                "success": True,
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "issue": issue,
                "priority": priority.lower(),
                "channel": channel.lower(),
                "status": "open",
                "created_at": created_at.isoformat(),
                "updated_at": created_at.isoformat(),
                "metadata": metadata or {}
            }

        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def update_ticket_status(
        ticket_id: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update ticket status with validation.

        Args:
            ticket_id: Ticket ID
            new_status: New status
            notes: Optional notes about the status change

        Returns:
            Dict with update result
        """
        try:
            logger.info(f"Updating ticket {ticket_id} to status: {new_status}")

            # Validate status
            valid_statuses = ["open", "processing", "escalated", "resolved", "closed"]
            if new_status.lower() not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

            # In a real implementation, we would:
            # 1. Fetch current ticket status from database
            # 2. Validate transition is allowed
            # 3. Update ticket status
            # 4. Record status change in history table

            # For now, mock the current status
            current_status = "open"  # Would fetch from DB

            # Validate transition
            if new_status.lower() not in TicketManager.VALID_TRANSITIONS.get(current_status, []):
                raise ValueError(
                    f"Invalid status transition from {current_status} to {new_status}"
                )

            updated_at = datetime.now(timezone.utc)

            # Verify database connection
            db_pool = get_db_pool()
            await db_pool.fetchval("SELECT 1")

            logger.info(f"Ticket {ticket_id} status updated to {new_status}")

            return {
                "success": True,
                "ticket_id": ticket_id,
                "old_status": current_status,
                "new_status": new_status.lower(),
                "notes": notes,
                "updated_at": updated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error updating ticket status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def escalate_ticket(
        ticket_id: str,
        reason: str,
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """
        Escalate ticket to human agent.

        Args:
            ticket_id: Ticket ID
            reason: Escalation reason
            urgency: Urgency level (low, medium, high)

        Returns:
            Dict with escalation result
        """
        try:
            logger.info(f"Escalating ticket {ticket_id}: {reason}")

            # Validate urgency
            valid_urgencies = ["low", "medium", "high"]
            if urgency.lower() not in valid_urgencies:
                raise ValueError(f"Invalid urgency. Must be one of: {valid_urgencies}")

            # Update ticket status to escalated
            result = await TicketManager.update_ticket_status(
                ticket_id,
                "escalated",
                notes=f"Escalated: {reason}"
            )

            if not result.get("success"):
                return result

            escalated_at = datetime.now(timezone.utc)

            return {
                "success": True,
                "ticket_id": ticket_id,
                "escalated": True,
                "reason": reason,
                "urgency": urgency.lower(),
                "escalated_at": escalated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error escalating ticket: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "escalated": False
            }

    @staticmethod
    async def resolve_ticket(
        ticket_id: str,
        resolution_notes: str
    ) -> Dict[str, Any]:
        """
        Resolve ticket with notes.

        Args:
            ticket_id: Ticket ID
            resolution_notes: Resolution notes

        Returns:
            Dict with resolution result
        """
        try:
            logger.info(f"Resolving ticket {ticket_id}")

            if not resolution_notes or not resolution_notes.strip():
                raise ValueError("Resolution notes are required")

            # Update ticket status to resolved
            result = await TicketManager.update_ticket_status(
                ticket_id,
                "resolved",
                notes=resolution_notes
            )

            if not result.get("success"):
                return result

            resolved_at = datetime.now(timezone.utc)

            return {
                "success": True,
                "ticket_id": ticket_id,
                "status": "resolved",
                "resolution_notes": resolution_notes,
                "resolved_at": resolved_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error resolving ticket: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def get_ticket_history(ticket_id: str) -> Dict[str, Any]:
        """
        Get ticket status change history.

        Args:
            ticket_id: Ticket ID

        Returns:
            Dict with ticket history
        """
        try:
            logger.info(f"Fetching history for ticket {ticket_id}")

            # Verify database connection
            db_pool = get_db_pool()
            await db_pool.fetchval("SELECT 1")

            # Mock history data
            history = [
                {
                    "status": "open",
                    "timestamp": "2026-04-07T10:00:00Z",
                    "notes": "Ticket created"
                },
                {
                    "status": "processing",
                    "timestamp": "2026-04-07T10:05:00Z",
                    "notes": "Agent started processing"
                }
            ]

            return {
                "success": True,
                "ticket_id": ticket_id,
                "history": history
            }

        except Exception as e:
            logger.error(f"Error fetching ticket history: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "history": []
            }

    @staticmethod
    async def get_open_tickets(
        limit: int = 50,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get open tickets.

        Args:
            limit: Maximum number of tickets to return
            priority: Optional priority filter

        Returns:
            Dict with open tickets
        """
        try:
            logger.info(f"Fetching open tickets (limit: {limit})")

            if priority:
                valid_priorities = ["low", "medium", "high", "urgent"]
                if priority.lower() not in valid_priorities:
                    raise ValueError(f"Invalid priority. Must be one of: {valid_priorities}")

            # Verify database connection
            db_pool = get_db_pool()
            await db_pool.fetchval("SELECT 1")

            # Mock open tickets data
            tickets = [
                {
                    "ticket_id": "ticket_001",
                    "customer_id": "customer@example.com",
                    "issue": "Login problem",
                    "priority": "high",
                    "status": "open",
                    "created_at": "2026-04-07T09:00:00Z"
                },
                {
                    "ticket_id": "ticket_002",
                    "customer_id": "user@example.com",
                    "issue": "Feature request",
                    "priority": "low",
                    "status": "processing",
                    "created_at": "2026-04-07T09:30:00Z"
                }
            ]

            # Filter by priority if specified
            if priority:
                tickets = [t for t in tickets if t["priority"] == priority.lower()]

            return {
                "success": True,
                "tickets": tickets[:limit],
                "total": len(tickets)
            }

        except Exception as e:
            logger.error(f"Error fetching open tickets: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tickets": []
            }
