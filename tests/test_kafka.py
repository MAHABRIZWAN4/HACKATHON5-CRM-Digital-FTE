"""Tests for Kafka components."""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.kafka.topics import KafkaTopics
from app.kafka.producer import KafkaProducerClient
from app.kafka.consumer import KafkaConsumerClient
from app.workers.message_processor import MessageProcessor
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db


@pytest_asyncio.fixture
async def db_setup():
    """Setup database for Kafka tests."""
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


class TestKafkaTopics:
    """Test Kafka topic definitions."""

    def test_all_topics_defined(self):
        """Test all required topics are defined."""
        assert KafkaTopics.TICKETS_INCOMING == "fte.tickets.incoming"
        assert KafkaTopics.EMAIL_INBOUND == "fte.channels.email.inbound"
        assert KafkaTopics.WHATSAPP_INBOUND == "fte.channels.whatsapp.inbound"
        assert KafkaTopics.WEBFORM_INBOUND == "fte.channels.webform.inbound"
        assert KafkaTopics.ESCALATIONS == "fte.escalations"
        assert KafkaTopics.METRICS == "fte.metrics"
        assert KafkaTopics.DLQ == "fte.dlq"

    def test_get_all_topics(self):
        """Test getting all topics."""
        topics = KafkaTopics.get_all_topics()

        assert len(topics) == 7
        assert KafkaTopics.TICKETS_INCOMING in topics
        assert KafkaTopics.DLQ in topics

    def test_get_channel_topic_gmail(self):
        """Test getting topic for gmail channel."""
        topic = KafkaTopics.get_channel_topic("gmail")
        assert topic == KafkaTopics.EMAIL_INBOUND

    def test_get_channel_topic_whatsapp(self):
        """Test getting topic for whatsapp channel."""
        topic = KafkaTopics.get_channel_topic("whatsapp")
        assert topic == KafkaTopics.WHATSAPP_INBOUND

    def test_get_channel_topic_web_form(self):
        """Test getting topic for web_form channel."""
        topic = KafkaTopics.get_channel_topic("web_form")
        assert topic == KafkaTopics.WEBFORM_INBOUND

    def test_get_channel_topic_unknown(self):
        """Test getting topic for unknown channel."""
        topic = KafkaTopics.get_channel_topic("unknown")
        assert topic == KafkaTopics.TICKETS_INCOMING


class TestKafkaProducer:
    """Test Kafka producer."""

    @pytest.mark.asyncio
    async def test_producer_initialization(self):
        """Test producer initializes correctly."""
        producer = KafkaProducerClient()

        assert producer.bootstrap_servers == "localhost:9092"
        assert producer.max_retries == 3
        assert producer.producer is None

    @pytest.mark.asyncio
    async def test_producer_start_stop(self):
        """Test producer start and stop."""
        producer = KafkaProducerClient()

        # Mock the AIOKafkaProducer
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer

            await producer.start()
            assert producer.producer is not None
            mock_producer.start.assert_called_once()

            await producer.stop()
            mock_producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_message_success(self):
        """Test successful message publishing."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_metadata = MagicMock()
            mock_metadata.partition = 0
            mock_metadata.offset = 123

            # Create inner future that resolves to metadata
            inner_future = asyncio.Future()
            inner_future.set_result(mock_metadata)

            # send() is async and returns an awaitable future
            mock_producer.send = AsyncMock(return_value=inner_future)
            mock_producer_class.return_value = mock_producer

            await producer.start()

            message = {"test": "data"}
            result = await producer.publish("test-topic", message)

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_ticket(self):
        """Test publishing ticket message."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_metadata = MagicMock()
            mock_metadata.partition = 0
            mock_metadata.offset = 123

            # Create inner future that resolves to metadata
            inner_future = asyncio.Future()
            inner_future.set_result(mock_metadata)

            # send() is async and returns an awaitable future
            mock_producer.send = AsyncMock(return_value=inner_future)
            mock_producer_class.return_value = mock_producer

            await producer.start()

            ticket_data = {
                "ticket_id": "ticket_123",
                "customer_id": "test@example.com",
                "message": "Test message",
                "channel": "gmail"
            }

            result = await producer.publish_ticket(ticket_data, "gmail")

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_escalation(self):
        """Test publishing escalation message."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_metadata = MagicMock()
            mock_metadata.partition = 0
            mock_metadata.offset = 123

            # Create inner future that resolves to metadata
            inner_future = asyncio.Future()
            inner_future.set_result(mock_metadata)

            # send() is async and returns an awaitable future
            mock_producer.send = AsyncMock(return_value=inner_future)
            mock_producer_class.return_value = mock_producer

            await producer.start()

            escalation_data = {
                "ticket_id": "ticket_123",
                "reason": "Customer requested human"
            }

            result = await producer.publish_escalation(escalation_data)

            assert result is True

    @pytest.mark.asyncio
    async def test_publish_metric(self):
        """Test publishing metric message."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_metadata = MagicMock()
            mock_metadata.partition = 0
            mock_metadata.offset = 123

            # Create inner future that resolves to metadata
            inner_future = asyncio.Future()
            inner_future.set_result(mock_metadata)

            # send() is async and returns an awaitable future
            mock_producer.send = AsyncMock(return_value=inner_future)
            mock_producer_class.return_value = mock_producer

            await producer.start()

            metric_data = {
                "ticket_id": "ticket_123",
                "success": True
            }

            result = await producer.publish_metric(metric_data)

            assert result is True


class TestKafkaConsumer:
    """Test Kafka consumer."""

    @pytest.mark.asyncio
    async def test_consumer_initialization(self):
        """Test consumer initializes correctly."""
        topics = ["test-topic"]
        consumer = KafkaConsumerClient("test-group", topics)

        assert consumer.bootstrap_servers == "localhost:9092"
        assert consumer.group_id == "test-group"
        assert consumer.topics == topics
        assert consumer.consumer is None
        assert consumer.running is False

    @pytest.mark.asyncio
    async def test_consumer_start_stop(self):
        """Test consumer start and stop."""
        consumer = KafkaConsumerClient("test-group", ["test-topic"])

        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer

            await consumer.start()
            assert consumer.consumer is not None
            assert consumer.running is True
            mock_consumer.start.assert_called_once()

            await consumer.stop()
            assert consumer.running is False
            mock_consumer.stop.assert_called_once()


class TestMessageProcessor:
    """Test message processor."""

    @pytest.mark.asyncio
    async def test_processor_initialization(self, db_setup, monkeypatch):
        """Test processor initializes correctly."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock get_producer to avoid Kafka connection
        with patch('app.workers.message_processor.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_get_producer.return_value = mock_producer

            await processor.initialize()

            assert processor.agent is not None
            assert processor.producer is not None

    @pytest.mark.asyncio
    async def test_process_email_message(self, db_setup, monkeypatch):
        """Test processing email message."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.handle_customer_inquiry = AsyncMock(return_value={
            "success": True,
            "escalation_triggered": False
        })
        processor.agent = mock_agent

        # Mock producer
        processor.producer = AsyncMock()

        message = {
            "ticket_id": "ticket_123",
            "customer_id": "test@example.com",
            "message": "I need help",
            "channel": "gmail",
            "customer_name": "Test User"
        }

        result = await processor.process_message(message, KafkaTopics.EMAIL_INBOUND)

        assert result is True
        mock_agent.handle_customer_inquiry.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_whatsapp_message(self, db_setup, monkeypatch):
        """Test processing WhatsApp message."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.handle_customer_inquiry = AsyncMock(return_value={
            "success": True,
            "escalation_triggered": False
        })
        processor.agent = mock_agent

        # Mock producer
        processor.producer = AsyncMock()

        message = {
            "ticket_id": "ticket_456",
            "customer_id": "whatsapp:+1234567890",
            "message": "Help needed",
            "channel": "whatsapp"
        }

        result = await processor.process_message(message, KafkaTopics.WHATSAPP_INBOUND)

        assert result is True
        mock_agent.handle_customer_inquiry.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_web_form_message(self, db_setup, monkeypatch):
        """Test processing web form message."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.handle_customer_inquiry = AsyncMock(return_value={
            "success": True,
            "escalation_triggered": False
        })
        processor.agent = mock_agent

        # Mock producer
        processor.producer = AsyncMock()

        message = {
            "ticket_id": "ticket_789",
            "customer_id": "user@example.com",
            "message": "Question about feature",
            "channel": "web_form",
            "customer_name": "Jane Doe"
        }

        result = await processor.process_message(message, KafkaTopics.WEBFORM_INBOUND)

        assert result is True
        mock_agent.handle_customer_inquiry.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_escalation(self, db_setup, monkeypatch):
        """Test processing message that triggers escalation."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock agent with escalation
        mock_agent = AsyncMock()
        mock_agent.handle_customer_inquiry = AsyncMock(return_value={
            "success": True,
            "escalation_triggered": True,
            "escalation_reason": "Customer requested human"
        })
        processor.agent = mock_agent

        # Mock producer
        mock_producer = AsyncMock()
        mock_producer.publish_escalation = AsyncMock(return_value=True)
        mock_producer.publish_metric = AsyncMock(return_value=True)
        processor.producer = mock_producer

        message = {
            "ticket_id": "ticket_escalate",
            "customer_id": "test@example.com",
            "message": "I want to speak to a human",
            "channel": "gmail"
        }

        result = await processor.process_message(message, KafkaTopics.EMAIL_INBOUND)

        assert result is True
        mock_producer.publish_escalation.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_missing_fields(self, db_setup, monkeypatch):
        """Test processing message with missing required fields."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()
        processor.agent = AsyncMock()
        processor.producer = AsyncMock()

        # Missing customer_id
        message = {
            "ticket_id": "ticket_123",
            "message": "Test",
            "channel": "gmail"
        }

        result = await processor.process_message(message, KafkaTopics.EMAIL_INBOUND)

        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_unknown_channel(self, db_setup, monkeypatch):
        """Test processing message with unknown channel."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()
        processor.agent = AsyncMock()
        processor.producer = AsyncMock()

        message = {
            "ticket_id": "ticket_123",
            "customer_id": "test@example.com",
            "message": "Test",
            "channel": "unknown_channel"
        }

        result = await processor.process_message(message, KafkaTopics.TICKETS_INCOMING)

        assert result is False


class TestMessageRouting:
    """Test message routing logic."""

    def test_route_to_correct_topic_gmail(self):
        """Test routing gmail messages to correct topic."""
        topic = KafkaTopics.get_channel_topic("gmail")
        assert topic == KafkaTopics.EMAIL_INBOUND

    def test_route_to_correct_topic_whatsapp(self):
        """Test routing whatsapp messages to correct topic."""
        topic = KafkaTopics.get_channel_topic("whatsapp")
        assert topic == KafkaTopics.WHATSAPP_INBOUND

    def test_route_to_correct_topic_web_form(self):
        """Test routing web form messages to correct topic."""
        topic = KafkaTopics.get_channel_topic("web_form")
        assert topic == KafkaTopics.WEBFORM_INBOUND


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    @pytest.mark.asyncio
    async def test_dlq_topic_exists(self):
        """Test DLQ topic is defined."""
        assert KafkaTopics.DLQ == "fte.dlq"

    @pytest.mark.asyncio
    async def test_failed_message_sent_to_dlq(self):
        """Test failed messages are sent to DLQ."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            # Simulate send failure
            mock_producer.send.side_effect = Exception("Send failed")
            mock_producer_class.return_value = mock_producer

            await producer.start()

            message = {"test": "data"}
            result = await producer.publish("test-topic", message)

            # Should fail but send to DLQ
            assert result is False
            # Check DLQ was called (second call after failure)
            assert mock_producer.send.call_count == 2


class TestErrorHandling:
    """Test error handling in Kafka components."""

    @pytest.mark.asyncio
    async def test_producer_handles_kafka_error(self):
        """Test producer handles Kafka errors gracefully."""
        producer = KafkaProducerClient()

        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            from aiokafka.errors import KafkaError
            mock_producer.send.side_effect = KafkaError("Kafka error")
            mock_producer_class.return_value = mock_producer

            await producer.start()

            result = await producer.publish("test-topic", {"test": "data"})

            assert result is False

    @pytest.mark.asyncio
    async def test_processor_handles_processing_error(self, db_setup, monkeypatch):
        """Test processor handles processing errors."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        processor = MessageProcessor()

        # Mock agent that raises error
        mock_agent = AsyncMock()
        mock_agent.handle_customer_inquiry = AsyncMock(side_effect=Exception("Processing error"))
        processor.agent = mock_agent
        processor.producer = AsyncMock()

        message = {
            "ticket_id": "ticket_error",
            "customer_id": "test@example.com",
            "message": "Test",
            "channel": "gmail"
        }

        result = await processor.process_message(message, KafkaTopics.EMAIL_INBOUND)

        assert result is False
