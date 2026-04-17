"""Escalation management and auto-escalation rules."""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.tickets.ticket_manager import TicketManager
from app.kafka.producer import get_producer
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class EscalationManager:
    """Manage ticket escalations and auto-escalation rules."""

    # Escalation trigger patterns
    LEGAL_PATTERNS = [
        r'\blawyer\b', r'\blegal\b', r'\bsue\b', r'\bsuing\b',
        r'\blawsuit\b', r'\bcourt\b', r'\battorney\b'
    ]

    AGGRESSIVE_PATTERNS = [
        r'\bstupid', r'\bidiot', r'\bterrible', r'\bawful',
        r'\bpathetic', r'\buseless', r'\bgarbage', r'\bscam'
    ]

    PRICING_PATTERNS = [
        r'\bprice\b', r'\bpricing\b', r'\bcost\b', r'\bexpensive\b',
        r'\bcheap\b', r'\bdiscount\b', r'\bbilling\b', r'\bcharge\b'
    ]

    REFUND_PATTERNS = [
        r'\brefund\b', r'\bmoney back\b', r'\breimburs', r'\bcancel\b.*\bsubscription\b'
    ]

    HUMAN_REQUEST_PATTERNS = [
        r'\bhuman\b', r'\breal person\b', r'\bagent\b', r'\bspeak.*someone\b',
        r'\btalk.*person\b', r'\brepresentative\b'
    ]

    @staticmethod
    def check_escalation_triggers(
        message: str,
        sentiment_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check if message triggers auto-escalation.

        Args:
            message: Customer message
            sentiment_score: Optional sentiment score (0-1)

        Returns:
            Dict with escalation decision and reason
        """
        try:
            message_lower = message.lower()
            triggers = []

            # Check legal threats
            if any(re.search(pattern, message_lower) for pattern in EscalationManager.LEGAL_PATTERNS):
                triggers.append("legal_threat")

            # Check aggressive language
            if any(re.search(pattern, message_lower) for pattern in EscalationManager.AGGRESSIVE_PATTERNS):
                triggers.append("aggressive_language")

            # Check pricing inquiries
            if any(re.search(pattern, message_lower) for pattern in EscalationManager.PRICING_PATTERNS):
                triggers.append("pricing_inquiry")

            # Check refund requests
            if any(re.search(pattern, message_lower) for pattern in EscalationManager.REFUND_PATTERNS):
                triggers.append("refund_request")

            # Check human request
            if any(re.search(pattern, message_lower) for pattern in EscalationManager.HUMAN_REQUEST_PATTERNS):
                triggers.append("human_requested")

            # Check sentiment
            if sentiment_score is not None and sentiment_score < 0.3:
                triggers.append("low_sentiment")

            should_escalate = len(triggers) > 0

            # Determine urgency based on triggers
            urgency = "low"
            if "legal_threat" in triggers or "aggressive_language" in triggers:
                urgency = "high"
            elif "refund_request" in triggers or "low_sentiment" in triggers:
                urgency = "medium"

            return {
                "should_escalate": should_escalate,
                "triggers": triggers,
                "urgency": urgency,
                "reason": ", ".join(triggers) if triggers else None
            }

        except Exception as e:
            logger.error(f"Error checking escalation triggers: {e}", exc_info=True)
            return {
                "should_escalate": False,
                "triggers": [],
                "urgency": "low",
                "reason": None,
                "error": str(e)
            }

    @staticmethod
    async def escalate_ticket(
        ticket_id: str,
        reason: str,
        urgency: str = "medium",
        customer_id: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Escalate ticket and notify human agents.

        Args:
            ticket_id: Ticket ID
            reason: Escalation reason
            urgency: Urgency level (low, medium, high)
            customer_id: Optional customer ID
            channel: Optional channel

        Returns:
            Dict with escalation result
        """
        try:
            logger.info(f"Escalating ticket {ticket_id}: {reason}")

            # Update ticket status
            result = await TicketManager.escalate_ticket(ticket_id, reason, urgency)

            if not result.get("success"):
                return result

            # Publish escalation to Kafka
            producer = await get_producer()
            escalation_data = {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "channel": channel,
                "reason": reason,
                "urgency": urgency,
                "escalated_at": datetime.now(timezone.utc).isoformat()
            }

            await producer.publish_escalation(escalation_data)

            logger.info(f"Escalation published for ticket {ticket_id}")

            return {
                "success": True,
                "ticket_id": ticket_id,
                "escalated": True,
                "reason": reason,
                "urgency": urgency,
                "escalated_at": result.get("escalated_at")
            }

        except Exception as e:
            logger.error(f"Error escalating ticket: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "escalated": False
            }

    @staticmethod
    def assign_priority(
        triggers: list,
        current_priority: str = "medium"
    ) -> str:
        """
        Assign priority based on escalation triggers.

        Args:
            triggers: List of escalation triggers
            current_priority: Current ticket priority

        Returns:
            Recommended priority level
        """
        try:
            # High priority triggers
            high_priority_triggers = ["legal_threat", "aggressive_language"]
            if any(t in triggers for t in high_priority_triggers):
                return "urgent"

            # Medium priority triggers
            medium_priority_triggers = ["refund_request", "low_sentiment"]
            if any(t in triggers for t in medium_priority_triggers):
                return "high"

            # Default to current priority or medium
            return current_priority if current_priority else "medium"

        except Exception as e:
            logger.error(f"Error assigning priority: {e}", exc_info=True)
            return "medium"

    @staticmethod
    async def notify_human_agents(
        ticket_id: str,
        urgency: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Notify human agents about escalation.

        Args:
            ticket_id: Ticket ID
            urgency: Urgency level
            reason: Escalation reason

        Returns:
            Dict with notification result
        """
        try:
            logger.info(f"Notifying human agents about ticket {ticket_id}")

            # In a real implementation, this would:
            # 1. Send notifications via email/Slack/etc
            # 2. Update agent dashboard
            # 3. Add to agent queue based on urgency

            notification_data = {
                "ticket_id": ticket_id,
                "urgency": urgency,
                "reason": reason,
                "notified_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Human agents notified for ticket {ticket_id}")

            return {
                "success": True,
                "notified": True,
                "notification_data": notification_data
            }

        except Exception as e:
            logger.error(f"Error notifying human agents: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "notified": False
            }

    @staticmethod
    def get_escalation_stats() -> Dict[str, Any]:
        """
        Get escalation statistics.

        Returns:
            Dict with escalation stats
        """
        try:
            # Mock stats - would query database in real implementation
            stats = {
                "total_escalations": 42,
                "escalations_by_trigger": {
                    "legal_threat": 5,
                    "aggressive_language": 8,
                    "pricing_inquiry": 12,
                    "refund_request": 10,
                    "human_requested": 15,
                    "low_sentiment": 7
                },
                "escalations_by_urgency": {
                    "low": 10,
                    "medium": 20,
                    "high": 12
                },
                "average_resolution_time_hours": 4.5
            }

            return {
                "success": True,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Error getting escalation stats: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "stats": {}
            }
