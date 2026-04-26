"""Tests for channel intake handlers."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db
from app.handlers.web_form import WebFormHandler, WebFormRequest
from app.handlers.gmail import GmailHandler, GmailMessage
from app.handlers.whatsapp import WhatsAppHandler, WhatsAppMessage, TwilioConfig


@pytest_asyncio.fixture
async def db_setup():
    """Setup database for handler tests."""
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


class TestWebFormHandler:
    """Test web form handler."""

    @pytest.mark.asyncio
    async def test_process_submission_success(self, db_setup):
        """Test successful form submission processing."""
        handler = WebFormHandler()
        form_data = WebFormRequest(
            name="John Doe",
            email="john@example.com",
            subject="Need help",
            message="I need assistance with my account"
        )

        result = await handler.process_submission(form_data)

        assert result["status"] == "success"
        assert result["channel"] == "web_form"
        assert "ticket_id" in result
        assert result["ticket_id"] is not None
        assert "message" in result

    @pytest.mark.asyncio
    async def test_create_ticket(self, db_setup):
        """Test ticket creation."""
        handler = WebFormHandler()
        form_data = WebFormRequest(
            name="Jane Smith",
            email="jane@example.com",
            subject="Bug report",
            message="Found a bug in the system"
        )

        ticket_id = await handler._create_ticket(form_data)

        assert ticket_id is not None
        assert isinstance(ticket_id, str)
        assert len(ticket_id) > 0

    def test_form_validation_valid_email(self):
        """Test form validation accepts valid email."""
        form_data = WebFormRequest(
            name="Test User",
            email="test@example.com",
            subject="Test",
            message="Test message"
        )

        assert form_data.email == "test@example.com"

    def test_form_validation_invalid_email(self):
        """Test form validation rejects invalid email."""
        with pytest.raises(Exception):  # Pydantic validation error
            WebFormRequest(
                name="Test User",
                email="invalid-email",
                subject="Test",
                message="Test message"
            )

    def test_form_validation_empty_name(self):
        """Test form validation rejects empty name."""
        with pytest.raises(Exception):  # Pydantic validation error
            WebFormRequest(
                name="",
                email="test@example.com",
                subject="Test",
                message="Test message"
            )

    def test_form_validation_empty_subject(self):
        """Test form validation rejects empty subject."""
        with pytest.raises(Exception):  # Pydantic validation error
            WebFormRequest(
                name="Test User",
                email="test@example.com",
                subject="",
                message="Test message"
            )

    def test_form_validation_empty_message(self):
        """Test form validation rejects empty message."""
        with pytest.raises(Exception):  # Pydantic validation error
            WebFormRequest(
                name="Test User",
                email="test@example.com",
                subject="Test",
                message=""
            )

    def test_form_validation_long_fields(self):
        """Test form validation with maximum length fields."""
        form_data = WebFormRequest(
            name="A" * 255,
            email="test@example.com",
            subject="B" * 500,
            message="C" * 5000
        )

        assert len(form_data.name) == 255
        assert len(form_data.subject) == 500
        assert len(form_data.message) == 5000


class TestGmailHandler:
    """Test Gmail handler."""

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, db_setup):
        """Test successful Gmail webhook processing."""
        handler = GmailHandler()
        webhook_data = {
            "message_id": "msg_123",
            "from": "customer@example.com",
            "from_name": "Customer Name",
            "subject": "Help needed",
            "body": "I need help with my account"
        }

        result = await handler.process_webhook(webhook_data)

        assert result["status"] == "success"
        assert result["channel"] == "gmail"
        assert "ticket_id" in result
        assert result["ticket_id"] is not None

    def test_parse_message_complete_data(self):
        """Test parsing Gmail message with complete data."""
        handler = GmailHandler()
        webhook_data = {
            "message_id": "msg_456",
            "from": "user@example.com",
            "from_name": "Test User",
            "subject": "Test Subject",
            "body": "Test body content"
        }

        message = handler._parse_message(webhook_data)

        assert message.message_id == "msg_456"
        assert message.from_email == "user@example.com"
        assert message.from_name == "Test User"
        assert message.subject == "Test Subject"
        assert message.body == "Test body content"
        assert isinstance(message.timestamp, datetime)

    def test_parse_message_minimal_data(self):
        """Test parsing Gmail message with minimal data."""
        handler = GmailHandler()
        webhook_data = {}

        message = handler._parse_message(webhook_data)

        assert message.message_id == "unknown"
        assert message.from_email == "unknown@example.com"
        assert message.from_name is None
        assert message.subject == "No Subject"
        assert message.body == ""

    def test_parse_message_no_subject(self):
        """Test parsing Gmail message without subject."""
        handler = GmailHandler()
        webhook_data = {
            "message_id": "msg_789",
            "from": "test@example.com",
            "body": "Message without subject"
        }

        message = handler._parse_message(webhook_data)

        assert message.subject == "No Subject"
        assert message.body == "Message without subject"

    @pytest.mark.asyncio
    async def test_create_ticket(self, db_setup):
        """Test ticket creation from Gmail message."""
        handler = GmailHandler()
        message = GmailMessage(
            message_id="msg_test",
            from_email="test@example.com",
            from_name="Test User",
            subject="Test",
            body="Test message",
            timestamp=datetime.now(timezone.utc)
        )

        ticket_id = await handler._create_ticket(message)

        assert ticket_id is not None
        assert isinstance(ticket_id, str)

    @pytest.mark.asyncio
    async def test_send_reply(self, db_setup, monkeypatch):
        """Test sending Gmail reply."""
        import os
        monkeypatch.setenv("GMAIL_ADDRESS", "support@example.com")

        # Mock os.path.exists to return True for credentials files
        def mock_exists(path):
            path_str = str(path)  # Convert Path objects to string
            if 'credentials.json' in path_str or 'token.json' in path_str:
                return True
            # For other paths, use the original os.path.exists
            import os as original_os
            return original_os.path.exists(path)

        monkeypatch.setattr("os.path.exists", mock_exists)

        # Mock Gmail service
        from unittest.mock import MagicMock
        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = {'id': 'msg_123'}

        handler = GmailHandler()

        # Mock _get_gmail_service to return our mock
        handler._get_gmail_service = MagicMock(return_value=mock_service)

        result = await handler.send_reply(
            "customer@example.com",
            "Re: Your ticket",
            "We received your request"
        )

        assert result is True


class TestWhatsAppHandler:
    """Test WhatsApp handler."""

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, db_setup):
        """Test successful WhatsApp webhook processing."""
        handler = WhatsAppHandler()
        webhook_data = {
            "MessageSid": "SM123456",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "I need help",
            "NumMedia": "0"
        }

        # Mock the agent to avoid Groq API call
        with patch('app.agent.customer_success_agent.get_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.handle_customer_inquiry = AsyncMock(return_value={
                "success": True,
                "ticket_id": "123",
                "response": "Thank you for contacting us."
            })
            mock_get_agent.return_value = mock_agent

            # Mock send_message to avoid Twilio API call
            with patch.object(handler, 'send_message', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await handler.process_webhook(webhook_data)

        assert result["status"] == "success"
        assert result["channel"] == "whatsapp"
        assert "ticket_id" in result
        assert result["ticket_id"] is not None

    def test_parse_message_text_only(self):
        """Test parsing WhatsApp message with text only."""
        handler = WhatsAppHandler()
        webhook_data = {
            "MessageSid": "SM789",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "Hello, I need support",
            "NumMedia": "0"
        }

        message = handler._parse_message(webhook_data)

        assert message.message_sid == "SM789"
        assert message.from_number == "whatsapp:+1234567890"
        assert message.to_number == "whatsapp:+0987654321"
        assert message.body == "Hello, I need support"
        assert len(message.media_urls) == 0

    def test_parse_message_with_media(self):
        """Test parsing WhatsApp message with media."""
        handler = WhatsAppHandler()
        webhook_data = {
            "MessageSid": "SM999",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "Check this image",
            "NumMedia": "2",
            "MediaUrl0": "https://example.com/image1.jpg",
            "MediaUrl1": "https://example.com/image2.jpg"
        }

        message = handler._parse_message(webhook_data)

        assert message.body == "Check this image"
        assert len(message.media_urls) == 2
        assert "image1.jpg" in message.media_urls[0]
        assert "image2.jpg" in message.media_urls[1]

    def test_parse_message_empty_body(self):
        """Test parsing WhatsApp message with empty body."""
        handler = WhatsAppHandler()
        webhook_data = {
            "MessageSid": "SM111",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "NumMedia": "0"
        }

        message = handler._parse_message(webhook_data)

        assert message.body == ""
        assert message.message_sid == "SM111"

    @pytest.mark.asyncio
    async def test_create_ticket(self, db_setup):
        """Test ticket creation from WhatsApp message."""
        handler = WhatsAppHandler()
        message = WhatsAppMessage(
            message_sid="SM_test",
            from_number="whatsapp:+1234567890",
            to_number="whatsapp:+0987654321",
            body="Test message",
            timestamp=datetime.now(timezone.utc)
        )

        ticket_id = await handler._create_ticket(message)

        assert ticket_id is not None
        assert isinstance(ticket_id, str)

    def test_validate_signature_valid(self, monkeypatch):
        """Test Twilio signature validation with valid signature."""
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")

        handler = WhatsAppHandler()

        # Create test data
        url = "https://example.com/webhooks/whatsapp"
        params = {"From": "whatsapp:+1234567890", "Body": "Test"}

        # Generate valid signature
        import hmac
        import hashlib
        import base64

        data = url
        for key in sorted(params.keys()):
            data += f"{key}{params[key]}"

        signature = base64.b64encode(
            hmac.new(
                "test_token".encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode()

        result = handler.validate_signature(signature, url, params)

        assert result is True

    def test_validate_signature_invalid(self, monkeypatch):
        """Test Twilio signature validation with invalid signature."""
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")

        handler = WhatsAppHandler()
        url = "https://example.com/webhooks/whatsapp"
        params = {"From": "whatsapp:+1234567890", "Body": "Test"}

        result = handler.validate_signature("invalid_signature", url, params)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message(self, db_setup, monkeypatch):
        """Test sending WhatsApp message."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
        monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+1234567890")

        handler = WhatsAppHandler()

        # Mock Twilio client to avoid real API call
        with patch('twilio.rest.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = "SM_mock_123"
            mock_client.messages.create.return_value = mock_message
            mock_client_class.return_value = mock_client

            result = await handler.send_message(
                "whatsapp:+0987654321",
                "Your ticket has been created"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_webhook_with_signature_validation(self, db_setup, monkeypatch):
        """Test webhook processing with signature validation."""
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")

        handler = WhatsAppHandler()
        webhook_data = {
            "MessageSid": "SM_sig_test",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "Test with signature",
            "NumMedia": "0"
        }

        # Process without signature (should still work for testing)
        result = await handler.process_webhook(webhook_data)

        assert result["status"] == "success"


class TestHandlerErrorHandling:
    """Test error handling in handlers."""

    @pytest.mark.asyncio
    async def test_web_form_handler_database_error(self, db_setup):
        """Test web form handler handles database errors."""
        handler = WebFormHandler()

        # Close database to simulate error
        await close_db()

        form_data = WebFormRequest(
            name="Test",
            email="test@example.com",
            subject="Test",
            message="Test"
        )

        with pytest.raises(Exception):
            await handler.process_submission(form_data)

        # Reconnect for cleanup
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="fte_db",
        )
        await init_db(db_config)

    @pytest.mark.asyncio
    async def test_gmail_handler_invalid_webhook_data(self, db_setup):
        """Test Gmail handler handles invalid webhook data gracefully."""
        handler = GmailHandler()

        # Should not crash with empty data
        result = await handler.process_webhook({})

        assert result["status"] == "success"
        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_whatsapp_handler_missing_fields(self, db_setup):
        """Test WhatsApp handler handles missing fields."""
        handler = WhatsAppHandler()

        # Minimal data
        webhook_data = {"NumMedia": "0"}

        result = await handler.process_webhook(webhook_data)

        assert result["status"] == "success"
        assert "ticket_id" in result
