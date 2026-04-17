"""Message processor worker."""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from app.kafka.consumer import KafkaConsumerClient
from app.kafka.producer import get_producer
from app.kafka.topics import KafkaTopics
from app.agent.customer_success_agent import get_agent
from app.handlers.gmail import gmail_handler
from app.handlers.whatsapp import whatsapp_handler
from app.handlers.web_form import web_form_handler
from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Process incoming messages from Kafka."""

    def __init__(self):
        """Initialize message processor."""
        self.agent = None
        self.producer = None

    async def initialize(self):
        """Initialize dependencies."""
        try:
            # Get agent instance
            self.agent = get_agent()

            # Get producer instance
            self.producer = await get_producer()

            logger.info("Message processor initialized")

        except Exception as e:
            logger.error(f"Failed to initialize message processor: {e}", exc_info=True)
            raise

    async def process_message(self, message: Dict[str, Any], topic: str) -> bool:
        """
        Process a message from Kafka.

        Args:
            message: Message payload
            topic: Topic the message came from

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            logger.info(f"Processing message from {topic}: {message.get('ticket_id')}")

            # Extract message data
            customer_id = message.get("customer_id")
            customer_message = message.get("message")
            channel = message.get("channel")
            ticket_id = message.get("ticket_id")

            if not all([customer_id, customer_message, channel]):
                logger.error("Missing required fields in message")
                return False

            # Route to appropriate handler based on channel
            if channel == "gmail":
                result = await self._process_email(message)
            elif channel == "whatsapp":
                result = await self._process_whatsapp(message)
            elif channel == "web_form":
                result = await self._process_web_form(message)
            else:
                logger.error(f"Unknown channel: {channel}")
                return False

            # Publish metrics
            await self._publish_metrics(message, result)

            # Check if escalation needed
            if result.get("escalation_triggered"):
                await self._handle_escalation(message, result)

            return result.get("success", False)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return False

    async def _process_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process email message."""
        try:
            logger.info(f"Processing email message: {message.get('ticket_id')}")

            # Use agent to handle inquiry
            result = await self.agent.handle_customer_inquiry(
                customer_id=message.get("customer_id"),
                message=message.get("message"),
                channel="gmail",
                customer_name=message.get("customer_name")
            )

            return result

        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _process_whatsapp(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process WhatsApp message."""
        try:
            logger.info(f"Processing WhatsApp message: {message.get('ticket_id')}")

            # Use agent to handle inquiry
            result = await self.agent.handle_customer_inquiry(
                customer_id=message.get("customer_id"),
                message=message.get("message"),
                channel="whatsapp"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing WhatsApp: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _process_web_form(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process web form message."""
        try:
            logger.info(f"Processing web form message: {message.get('ticket_id')}")

            # Use agent to handle inquiry
            result = await self.agent.handle_customer_inquiry(
                customer_id=message.get("customer_id"),
                message=message.get("message"),
                channel="web_form",
                customer_name=message.get("customer_name")
            )

            return result

        except Exception as e:
            logger.error(f"Error processing web form: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _handle_escalation(
        self,
        message: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Handle escalation by publishing to escalations topic."""
        try:
            escalation_data = {
                "ticket_id": message.get("ticket_id"),
                "customer_id": message.get("customer_id"),
                "channel": message.get("channel"),
                "reason": result.get("escalation_reason"),
                "original_message": message.get("message"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.producer.publish_escalation(escalation_data)
            logger.info(f"Escalation published for ticket: {message.get('ticket_id')}")

        except Exception as e:
            logger.error(f"Error handling escalation: {e}", exc_info=True)

    async def _publish_metrics(
        self,
        message: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Publish processing metrics."""
        try:
            metric_data = {
                "ticket_id": message.get("ticket_id"),
                "channel": message.get("channel"),
                "success": result.get("success", False),
                "escalated": result.get("escalation_triggered", False),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.producer.publish_metric(metric_data)

        except Exception as e:
            logger.error(f"Error publishing metrics: {e}", exc_info=True)


async def start_worker():
    """Start the message processor worker."""
    logger.info("Starting message processor worker...")

    # Initialize processor
    processor = MessageProcessor()
    await processor.initialize()

    # Create consumer for all channel topics
    topics = [
        KafkaTopics.EMAIL_INBOUND,
        KafkaTopics.WHATSAPP_INBOUND,
        KafkaTopics.WEBFORM_INBOUND,
        KafkaTopics.TICKETS_INCOMING
    ]

    consumer = KafkaConsumerClient(
        group_id="fte-message-processor",
        topics=topics
    )

    try:
        await consumer.start()

        # Start consuming messages
        await consumer.consume(processor.process_message)

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)

    finally:
        await consumer.stop()
        logger.info("Message processor worker stopped")
