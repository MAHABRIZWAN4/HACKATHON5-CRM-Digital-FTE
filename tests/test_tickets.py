"""Tests for ticket lifecycle and escalation management."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.tickets.ticket_manager import TicketManager
from app.tickets.escalation_manager import EscalationManager
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db


@pytest_asyncio.fixture
async def db_setup():
    """Setup database for ticket tests."""
    db_config = DatabaseConfig(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="fte_db",
        pool_min_size=2,
        pool_max_size=5,
        pool_timeout=10.0,
    )
    await init_db(db_config)
    yield
    await close_db()


class TestTicketCreation:
    """Test ticket creation."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, db_setup):
        """Test successful ticket creation."""
        result = await TicketManager.create_ticket(
            customer_id="test@example.com",
            issue="Login problem",
            priority="high",
            channel="gmail"
        )

        assert result["success"] is True
        assert "ticket_id" in result
        assert result["customer_id"] == "test@example.com"
        assert result["priority"] == "high"
        assert result["channel"] == "gmail"
        assert result["status"] == "open"
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_ticket_with_metadata(self, db_setup):
        """Test ticket creation with metadata."""
        metadata = {"source": "web", "browser": "Chrome"}
        result = await TicketManager.create_ticket(
            customer_id="user@example.com",
            issue="Feature request",
            priority="low",
            channel="web_form",
            customer_name="John Doe",
            metadata=metadata
        )

        assert result["success"] is True
        assert result["customer_name"] == "John Doe"
        assert result["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_priority(self, db_setup):
        """Test ticket creation with invalid priority."""
        result = await TicketManager.create_ticket(
            customer_id="test@example.com",
            issue="Test issue",
            priority="invalid",
            channel="gmail"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_channel(self, db_setup):
        """Test ticket creation with invalid channel."""
        result = await TicketManager.create_ticket(
            customer_id="test@example.com",
            issue="Test issue",
            priority="medium",
            channel="invalid_channel"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_ticket_all_priorities(self, db_setup):
        """Test ticket creation with all valid priorities."""
        priorities = ["low", "medium", "high", "urgent"]

        for priority in priorities:
            result = await TicketManager.create_ticket(
                customer_id="test@example.com",
                issue=f"Test issue - {priority}",
                priority=priority,
                channel="gmail"
            )
            assert result["success"] is True
            assert result["priority"] == priority

    @pytest.mark.asyncio
    async def test_create_ticket_all_channels(self, db_setup):
        """Test ticket creation with all valid channels."""
        channels = ["gmail", "whatsapp", "web_form"]

        for channel in channels:
            result = await TicketManager.create_ticket(
                customer_id="test@example.com",
                issue=f"Test issue - {channel}",
                priority="medium",
                channel=channel
            )
            assert result["success"] is True
            assert result["channel"] == channel


class TestStatusTransitions:
    """Test ticket status transitions."""

    @pytest.mark.asyncio
    async def test_update_status_valid_transition(self, db_setup):
        """Test valid status transition."""
        result = await TicketManager.update_ticket_status(
            ticket_id="ticket_123",
            new_status="processing"
        )

        assert result["success"] is True
        assert result["new_status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_status_with_notes(self, db_setup):
        """Test status update with notes."""
        result = await TicketManager.update_ticket_status(
            ticket_id="ticket_123",
            new_status="processing",
            notes="Agent started working on ticket"
        )

        assert result["success"] is True
        assert result["notes"] == "Agent started working on ticket"

    @pytest.mark.asyncio
    async def test_update_status_invalid_status(self, db_setup):
        """Test status update with invalid status."""
        result = await TicketManager.update_ticket_status(
            ticket_id="ticket_123",
            new_status="invalid_status"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_valid_transitions_defined(self):
        """Test that valid transitions are properly defined."""
        transitions = TicketManager.VALID_TRANSITIONS

        assert "open" in transitions
        assert "processing" in transitions["open"]
        assert "resolved" in transitions["processing"]
        assert "escalated" in transitions["processing"]
        assert "closed" in transitions["resolved"]

    @pytest.mark.asyncio
    async def test_status_transition_timestamps(self, db_setup):
        """Test that status transitions include timestamps."""
        result = await TicketManager.update_ticket_status(
            ticket_id="ticket_123",
            new_status="processing"
        )

        assert result["success"] is True
        assert "updated_at" in result


class TestEscalationRules:
    """Test escalation trigger detection."""

    def test_legal_threat_detection(self):
        """Test detection of legal threats."""
        messages = [
            "I'm going to sue you",
            "My lawyer will contact you",
            "See you in court",
            "I'll file a lawsuit"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is True
            assert "legal_threat" in result["triggers"]
            assert result["urgency"] == "high"

    def test_aggressive_language_detection(self):
        """Test detection of aggressive language."""
        messages = [
            "This is stupid",
            "You're all idiots",
            "Terrible service",
            "This is a scam"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is True
            assert "aggressive_language" in result["triggers"]
            assert result["urgency"] == "high"

    def test_pricing_inquiry_detection(self):
        """Test detection of pricing inquiries."""
        messages = [
            "What's the price?",
            "This is too expensive",
            "Can I get a discount?",
            "How much does it cost?"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is True
            assert "pricing_inquiry" in result["triggers"]

    def test_refund_request_detection(self):
        """Test detection of refund requests."""
        messages = [
            "I want a refund",
            "Give me my money back",
            "I need to cancel my subscription",
            "Please reimburse me"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is True
            assert "refund_request" in result["triggers"]
            assert result["urgency"] == "medium"

    def test_human_request_detection(self):
        """Test detection of human agent requests."""
        messages = [
            "I want to speak to a human",
            "Can I talk to a real person?",
            "Connect me to an agent",
            "I need a representative"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is True
            assert "human_requested" in result["triggers"]

    def test_low_sentiment_detection(self):
        """Test detection of low sentiment."""
        result = EscalationManager.check_escalation_triggers(
            "I'm very unhappy",
            sentiment_score=0.2
        )

        assert result["should_escalate"] is True
        assert "low_sentiment" in result["triggers"]
        assert result["urgency"] == "medium"

    def test_no_escalation_needed(self):
        """Test messages that don't need escalation."""
        messages = [
            "How do I reset my password?",
            "Can you help me with this feature?",
            "Thank you for your help"
        ]

        for message in messages:
            result = EscalationManager.check_escalation_triggers(message)
            assert result["should_escalate"] is False
            assert len(result["triggers"]) == 0

    def test_multiple_triggers(self):
        """Test message with multiple escalation triggers."""
        message = "This is terrible and I want a refund now!"
        result = EscalationManager.check_escalation_triggers(message)

        assert result["should_escalate"] is True
        assert "aggressive_language" in result["triggers"]
        assert "refund_request" in result["triggers"]
        assert result["urgency"] == "high"


class TestTicketEscalation:
    """Test ticket escalation flow."""

    @pytest.mark.asyncio
    async def test_escalate_ticket_success(self, db_setup):
        """Test successful ticket escalation."""
        with patch('app.tickets.escalation_manager.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_escalation = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await EscalationManager.escalate_ticket(
                ticket_id="ticket_123",
                reason="Customer requested human",
                urgency="medium"
            )

            assert result["success"] is True
            assert result["escalated"] is True
            assert result["reason"] == "Customer requested human"
            assert result["urgency"] == "medium"
            mock_producer.publish_escalation.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalate_ticket_with_customer_info(self, db_setup):
        """Test escalation with customer information."""
        with patch('app.tickets.escalation_manager.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_escalation = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await EscalationManager.escalate_ticket(
                ticket_id="ticket_123",
                reason="Legal threat",
                urgency="high",
                customer_id="test@example.com",
                channel="gmail"
            )

            assert result["success"] is True
            assert result["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_escalate_ticket_invalid_urgency(self, db_setup):
        """Test escalation with invalid urgency."""
        result = await TicketManager.escalate_ticket(
            ticket_id="ticket_123",
            reason="Test",
            urgency="invalid"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_assign_priority_high_triggers(self):
        """Test priority assignment for high-priority triggers."""
        triggers = ["legal_threat"]
        priority = EscalationManager.assign_priority(triggers)
        assert priority == "urgent"

        triggers = ["aggressive_language"]
        priority = EscalationManager.assign_priority(triggers)
        assert priority == "urgent"

    @pytest.mark.asyncio
    async def test_assign_priority_medium_triggers(self):
        """Test priority assignment for medium-priority triggers."""
        triggers = ["refund_request"]
        priority = EscalationManager.assign_priority(triggers)
        assert priority == "high"

        triggers = ["low_sentiment"]
        priority = EscalationManager.assign_priority(triggers)
        assert priority == "high"

    @pytest.mark.asyncio
    async def test_notify_human_agents(self):
        """Test human agent notification."""
        result = await EscalationManager.notify_human_agents(
            ticket_id="ticket_123",
            urgency="high",
            reason="Legal threat"
        )

        assert result["success"] is True
        assert result["notified"] is True


class TestTicketResolution:
    """Test ticket resolution flow."""

    @pytest.mark.asyncio
    async def test_resolve_ticket_success(self, db_setup):
        """Test successful ticket resolution."""
        result = await TicketManager.resolve_ticket(
            ticket_id="ticket_123",
            resolution_notes="Issue resolved by providing password reset link"
        )

        assert result["success"] is True
        assert result["status"] == "resolved"
        assert "resolution_notes" in result
        assert "resolved_at" in result

    @pytest.mark.asyncio
    async def test_resolve_ticket_empty_notes(self, db_setup):
        """Test resolution with empty notes."""
        result = await TicketManager.resolve_ticket(
            ticket_id="ticket_123",
            resolution_notes=""
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_resolve_ticket_whitespace_notes(self, db_setup):
        """Test resolution with whitespace-only notes."""
        result = await TicketManager.resolve_ticket(
            ticket_id="ticket_123",
            resolution_notes="   "
        )

        assert result["success"] is False
        assert "error" in result


class TestTicketHistory:
    """Test ticket history tracking."""

    @pytest.mark.asyncio
    async def test_get_ticket_history(self, db_setup):
        """Test fetching ticket history."""
        result = await TicketManager.get_ticket_history("ticket_123")

        assert result["success"] is True
        assert "history" in result
        assert isinstance(result["history"], list)

    @pytest.mark.asyncio
    async def test_ticket_history_structure(self, db_setup):
        """Test ticket history has correct structure."""
        result = await TicketManager.get_ticket_history("ticket_123")

        assert result["success"] is True
        if len(result["history"]) > 0:
            entry = result["history"][0]
            assert "status" in entry
            assert "timestamp" in entry
            assert "notes" in entry


class TestOpenTickets:
    """Test open tickets retrieval."""

    @pytest.mark.asyncio
    async def test_get_open_tickets(self, db_setup):
        """Test fetching open tickets."""
        result = await TicketManager.get_open_tickets()

        assert result["success"] is True
        assert "tickets" in result
        assert isinstance(result["tickets"], list)

    @pytest.mark.asyncio
    async def test_get_open_tickets_with_limit(self, db_setup):
        """Test fetching open tickets with limit."""
        result = await TicketManager.get_open_tickets(limit=10)

        assert result["success"] is True
        assert len(result["tickets"]) <= 10

    @pytest.mark.asyncio
    async def test_get_open_tickets_by_priority(self, db_setup):
        """Test fetching open tickets filtered by priority."""
        result = await TicketManager.get_open_tickets(priority="high")

        assert result["success"] is True
        # All returned tickets should have high priority
        for ticket in result["tickets"]:
            assert ticket["priority"] == "high"

    @pytest.mark.asyncio
    async def test_get_open_tickets_invalid_priority(self, db_setup):
        """Test fetching open tickets with invalid priority."""
        result = await TicketManager.get_open_tickets(priority="invalid")

        assert result["success"] is False
        assert "error" in result


class TestEscalationStats:
    """Test escalation statistics."""

    def test_get_escalation_stats(self):
        """Test fetching escalation statistics."""
        result = EscalationManager.get_escalation_stats()

        assert result["success"] is True
        assert "stats" in result
        assert "total_escalations" in result["stats"]
        assert "escalations_by_trigger" in result["stats"]
        assert "escalations_by_urgency" in result["stats"]


class TestErrorHandling:
    """Test error handling in ticket management."""

    @pytest.mark.asyncio
    async def test_create_ticket_handles_database_error(self, db_setup):
        """Test ticket creation handles database errors."""
        with patch('app.tickets.ticket_manager.get_db_pool') as mock_pool:
            mock_pool.side_effect = Exception("Database error")

            result = await TicketManager.create_ticket(
                customer_id="test@example.com",
                issue="Test",
                priority="medium",
                channel="gmail"
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_escalation_handles_kafka_error(self, db_setup):
        """Test escalation handles Kafka errors."""
        with patch('app.tickets.escalation_manager.get_producer') as mock_get_producer:
            mock_get_producer.side_effect = Exception("Kafka error")

            result = await EscalationManager.escalate_ticket(
                ticket_id="ticket_123",
                reason="Test",
                urgency="medium"
            )

            assert result["success"] is False
            assert "error" in result
