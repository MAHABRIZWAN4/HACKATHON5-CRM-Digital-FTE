"""Kafka producer for publishing messages."""

import os
import json
import logging
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """Async Kafka producer client."""

    def __init__(self):
        """Initialize Kafka producer."""
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.producer: Optional[AIOKafkaProducer] = None
        self.max_retries = int(os.getenv("KAFKA_MAX_RETRIES", "3"))

    async def start(self):
        """Start the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                compression_type='gzip'
            )
            await self.producer.start()
            logger.info(f"Kafka producer started: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}", exc_info=True)

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Publish message to Kafka topic.

        Args:
            topic: Kafka topic name
            message: Message payload (will be JSON serialized)
            key: Optional message key for partitioning

        Returns:
            True if published successfully, False otherwise
        """
        if not self.producer:
            logger.error("Producer not started. Call start() first.")
            return False

        try:
            # Send message
            future = await self.producer.send(topic, value=message, key=key)
            record_metadata = await future

            logger.info(
                f"Message published to {topic} "
                f"(partition: {record_metadata.partition}, "
                f"offset: {record_metadata.offset})"
            )
            return True

        except KafkaError as e:
            logger.error(f"Kafka error publishing to {topic}: {e}", exc_info=True)
            # Send to DLQ
            await self._send_to_dlq(topic, message, str(e))
            return False

        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}", exc_info=True)
            await self._send_to_dlq(topic, message, str(e))
            return False

    async def _send_to_dlq(
        self,
        original_topic: str,
        message: Dict[str, Any],
        error: str
    ):
        """Send failed message to dead letter queue."""
        try:
            dlq_message = {
                "original_topic": original_topic,
                "original_message": message,
                "error": error,
                "timestamp": message.get("timestamp")
            }

            await self.producer.send(KafkaTopics.DLQ, value=dlq_message)
            logger.info(f"Message sent to DLQ from {original_topic}")

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}", exc_info=True)

    async def publish_ticket(
        self,
        ticket_data: Dict[str, Any],
        channel: str
    ) -> bool:
        """
        Publish ticket to appropriate topic.

        Args:
            ticket_data: Ticket information
            channel: Channel (gmail, whatsapp, web_form)

        Returns:
            True if published successfully
        """
        # Get channel-specific topic
        topic = KafkaTopics.get_channel_topic(channel)

        # Use ticket_id as key for partitioning
        key = ticket_data.get("ticket_id")

        return await self.publish(topic, ticket_data, key)

    async def publish_escalation(self, escalation_data: Dict[str, Any]) -> bool:
        """Publish escalation to escalations topic."""
        return await self.publish(
            KafkaTopics.ESCALATIONS,
            escalation_data,
            escalation_data.get("ticket_id")
        )

    async def publish_metric(self, metric_data: Dict[str, Any]) -> bool:
        """Publish metric to metrics topic."""
        return await self.publish(KafkaTopics.METRICS, metric_data)


# Singleton instance
_producer_instance: Optional[KafkaProducerClient] = None


async def get_producer() -> KafkaProducerClient:
    """Get or create producer instance."""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducerClient()
        await _producer_instance.start()
    return _producer_instance


async def close_producer():
    """Close producer instance."""
    global _producer_instance
    if _producer_instance:
        await _producer_instance.stop()
        _producer_instance = None
