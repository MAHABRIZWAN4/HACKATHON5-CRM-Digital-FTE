"""Tests for Customer Success Agent."""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db
from app.agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response
)
from app.agent.formatters import (
    ResponseFormatter,
    detect_escalation_triggers
)
from app.agent.customer_success_agent import CustomerSuccessAgent


@pytest_asyncio.fixture
async def db_setup():
    """Setup database for agent tests."""
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


class TestTools:
    """Test agent tools."""

    @pytest.mark.asyncio
    async def test_search_knowledge_base_success(self, db_setup):
        """Test successful knowledge base search."""
        result = await search_knowledge_base("how to login", max_results=3)

        assert result["success"] is True
        assert "results" in result
        assert len(result["results"]) <= 3
        assert result["query"] == "how to login"

    @pytest.mark.asyncio
    async def test_search_knowledge_base_max_results_validation(self, db_setup):
        """Test max_results validation."""
        # Should work with valid range
        result = await search_knowledge_base("test", max_results=10)
        assert result["success"] is True

        # Should handle invalid range gracefully
        result = await search_knowledge_base("test", max_results=0)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, db_setup):
        """Test successful ticket creation."""
        result = await create_ticket(
            customer_id="test@example.com",
            issue="Cannot login to account",
            priority="high",
            channel="gmail"
        )

        assert result["success"] is True
        assert "ticket_id" in result
        assert result["customer_id"] == "test@example.com"
        assert result["priority"] == "high"
        assert result["channel"] == "gmail"
        assert result["status"] == "open"

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_priority(self, db_setup):
        """Test ticket creation with invalid priority."""
        result = await create_ticket(
            customer_id="test@example.com",
            issue="Test issue",
            priority="invalid_priority",
            channel="gmail"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_channel(self, db_setup):
        """Test ticket creation with invalid channel."""
        result = await create_ticket(
            customer_id="test@example.com",
            issue="Test issue",
            priority="medium",
            channel="invalid_channel"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_customer_history_success(self, db_setup):
        """Test fetching customer history."""
        result = await get_customer_history("test@example.com")

        assert result["success"] is True
        assert "history" in result
        assert result["history"]["customer_id"] == "test@example.com"
        assert "total_tickets" in result["history"]
        assert "recent_tickets" in result["history"]

    @pytest.mark.asyncio
    async def test_escalate_to_human_success(self, db_setup):
        """Test successful escalation."""
        result = await escalate_to_human(
            ticket_id="00000000-0000-0000-0000-000000000001",
            reason="Customer requested human agent",
            urgency="high"
        )

        assert result["success"] is True
        assert result["escalated"] is True
        assert result["ticket_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_escalate_to_human_invalid_urgency(self, db_setup):
        """Test escalation with invalid urgency."""
        result = await escalate_to_human(
            ticket_id="00000000-0000-0000-0000-000000000001",
            reason="Test",
            urgency="invalid_urgency"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_response_success(self, db_setup):
        """Test sending response."""
        # Create a ticket first
        ticket_result = await create_ticket(
            "test@example.com", "Test issue", "medium", "gmail"
        )
        assert ticket_result["success"] is True
        ticket_id = ticket_result["ticket_id"]

        # Now test sending response
        result = await send_response(
            ticket_id=ticket_id,
            message="Thank you for contacting us",
            channel="gmail"
        )

        assert result["success"] is True
        assert result["message_sent"] is True
        assert result["ticket_id"] == ticket_id
        assert result["channel"] == "gmail"
        assert "formatted_message" in result

    @pytest.mark.asyncio
    async def test_send_response_invalid_channel(self, db_setup):
        """Test sending response with invalid channel."""
        result = await send_response(
            ticket_id="123e4567-e89b-12d3-a456-426614174000",
            message="Test message",
            channel="invalid_channel"
        )

        assert result["success"] is False
        assert "error" in result


class TestResponseFormatter:
    """Test response formatters."""

    def test_format_for_email_with_name(self):
        """Test email formatting with customer name."""
        message = "Your issue has been resolved."
        formatted = ResponseFormatter.format_for_email(message, "John Doe")

        assert "Dear John Doe," in formatted
        assert message in formatted
        assert "Best regards" in formatted
        assert "Customer Success Team" in formatted

    def test_format_for_email_without_name(self):
        """Test email formatting without customer name."""
        message = "Your issue has been resolved."
        formatted = ResponseFormatter.format_for_email(message)

        assert "Hello," in formatted
        assert message in formatted
        assert "Best regards" in formatted

    def test_format_for_whatsapp_short_message(self):
        """Test WhatsApp formatting with short message."""
        message = "Thanks for reaching out!"
        formatted = ResponseFormatter.format_for_whatsapp(message)

        assert formatted == message
        assert len(formatted) <= 300

    def test_format_for_whatsapp_long_message(self):
        """Test WhatsApp formatting with long message."""
        message = "A" * 400  # Message longer than 300 chars
        formatted = ResponseFormatter.format_for_whatsapp(message)

        assert len(formatted) <= 300
        assert formatted.endswith("...")

    def test_format_for_web_form(self):
        """Test web form formatting."""
        message = "Your ticket has been created."
        formatted = ResponseFormatter.format_for_web_form(message)

        assert formatted == message

    def test_format_response_gmail(self):
        """Test format_response for gmail channel."""
        message = "Test message"
        formatted = ResponseFormatter.format_response(message, "gmail", "Jane")

        assert "Dear Jane," in formatted
        assert message in formatted

    def test_format_response_whatsapp(self):
        """Test format_response for whatsapp channel."""
        message = "Test message"
        formatted = ResponseFormatter.format_response(message, "whatsapp")

        assert formatted == message

    def test_format_response_web_form(self):
        """Test format_response for web_form channel."""
        message = "Test message"
        formatted = ResponseFormatter.format_response(message, "web_form")

        assert formatted == message


class TestEscalationTriggers:
    """Test escalation trigger detection."""

    def test_legal_threat_detection(self):
        """Test detection of legal threats."""
        messages = [
            "I'm going to sue you",
            "My lawyer will contact you",
            "See you in court",
            "I'll take legal action"
        ]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is True
            assert "legal" in result["reason"].lower()
            assert result["urgency"] == "high"

    def test_aggressive_language_detection(self):
        """Test detection of aggressive language."""
        messages = [
            "This is fucking ridiculous",
            "You're all idiots",
            "This is stupid"
        ]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is True
            assert "aggressive" in result["reason"].lower()

    def test_human_request_detection(self):
        """Test detection of human agent requests."""
        messages = [
            "I want to speak to a human",
            "Can I talk to a real person?",
            "I need a human agent"
        ]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is True
            assert "human" in result["reason"].lower()

    def test_whatsapp_human_keyword(self):
        """Test WhatsApp-specific human keywords."""
        messages = ["human", "agent", "HUMAN", "AGENT"]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is True

    def test_pricing_billing_detection(self):
        """Test detection of pricing/billing inquiries."""
        messages = [
            "How much does this cost?",
            "I want a refund",
            "What's the pricing?",
            "Billing issue"
        ]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is True
            assert "pricing" in result["reason"].lower() or "billing" in result["reason"].lower()

    def test_no_escalation_needed(self):
        """Test messages that don't need escalation."""
        messages = [
            "How do I reset my password?",
            "I need help with login",
            "Can you explain this feature?"
        ]

        for msg in messages:
            result = detect_escalation_triggers(msg)
            assert result["should_escalate"] is False
            assert result["reason"] is None


class TestAgentInitialization:
    """Test agent initialization."""

    def test_agent_initialization_with_api_key(self, monkeypatch):
        """Test agent initializes with API key."""
        monkeypatch.setenv("GROQ_API_KEY", "test_key_123")

        agent = CustomerSuccessAgent()

        assert agent.api_key == "test_key_123"
        assert agent.model == "llama-3.3-70b-versatile"
        assert agent.agent_name == "Customer Success FTE"
        assert len(agent.tools) == 5

    def test_agent_initialization_without_api_key(self, monkeypatch):
        """Test agent fails without API key."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            CustomerSuccessAgent()

    def test_agent_custom_model(self, monkeypatch):
        """Test agent with custom model."""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")
        monkeypatch.setenv("GROQ_MODEL", "llama-3.1-70b-versatile")

        agent = CustomerSuccessAgent()

        assert agent.model == "llama-3.1-70b-versatile"

    def test_agent_tools_defined(self, monkeypatch):
        """Test all required tools are defined."""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")

        agent = CustomerSuccessAgent()

        tool_names = [tool["function"]["name"] for tool in agent.tools]

        assert "search_knowledge_base" in tool_names
        assert "create_ticket" in tool_names
        assert "get_customer_history" in tool_names
        assert "escalate_to_human" in tool_names
        assert "send_response" in tool_names


class TestAgentErrorHandling:
    """Test agent error handling."""

    @pytest.mark.asyncio
    async def test_tool_execution_with_invalid_tool(self, monkeypatch, db_setup):
        """Test error handling for invalid tool."""
        monkeypatch.setenv("GROQ_API_KEY", "test_key")

        agent = CustomerSuccessAgent()

        with pytest.raises(ValueError, match="Unknown tool"):
            await agent._execute_tool("invalid_tool", {})

    @pytest.mark.asyncio
    async def test_handle_inquiry_with_missing_openai_key(self, monkeypatch, db_setup):
        """Test handling inquiry without Groq API key."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(ValueError):
            agent = CustomerSuccessAgent()


class TestToolIntegration:
    """Test tool integration with database."""

    @pytest.mark.asyncio
    async def test_all_tools_connect_to_database(self, db_setup):
        """Test that all tools can connect to database."""
        # Test create_ticket
        result = await create_ticket(
            "test@example.com", "Test", "medium", "gmail"
        )
        assert result["success"] is True
        ticket_id = result["ticket_id"]

        # Test get_customer_history
        result = await get_customer_history("test@example.com")
        assert result["success"] is True

        # Test search_knowledge_base
        result = await search_knowledge_base("test")
        assert result["success"] is True

        # Test escalate_to_human
        result = await escalate_to_human(ticket_id, "test", "low")
        assert result["success"] is True

        # Test send_response with actual ticket_id
        result = await send_response(ticket_id, "test", "gmail")
        assert result["success"] is True
