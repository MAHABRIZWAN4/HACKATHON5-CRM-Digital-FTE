"""Kafka consumer for receiving messages."""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaConsumerClient:
    """Async Kafka consumer client."""

    def __init__(self, group_id: str, topics: list):
        """
        Initialize Kafka consumer.

        Args:
            group_id: Consumer group ID
            topics: List of topics to subscribe to
        """
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.group_id = group_id
        self.topics = topics
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

    async def start(self):
        """Start the Kafka consumer."""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=False,  # Manual commit for reliability
                max_poll_records=10
            )
            await self.consumer.start()
            self.running = True
            logger.info(
                f"Kafka consumer started: group={self.group_id}, "
                f"topics={self.topics}"
            )
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the Kafka consumer."""
        self.running = False
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}", exc_info=True)

    async def consume(
        self,
        message_handler: Callable[[Dict[str, Any], str], Awaitable[bool]]
    ):
        """
        Consume messages and process them with handler.

        Args:
            message_handler: Async function to process each message.
                            Should return True if processed successfully.
        """
        if not self.consumer:
            logger.error("Consumer not started. Call start() first.")
            return

        logger.info("Starting message consumption...")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    logger.info(
                        f"Received message from {message.topic} "
                        f"(partition: {message.partition}, offset: {message.offset})"
                    )

                    # Process message
                    success = await message_handler(message.value, message.topic)

                    if success:
                        # Commit offset on success
                        await self.consumer.commit()
                        logger.info(f"Message processed and committed: offset {message.offset}")
                    else:
                        logger.warning(f"Message processing failed: offset {message.offset}")
                        # Don't commit - message will be reprocessed

                except Exception as e:
                    logger.error(
                        f"Error processing message from {message.topic}: {e}",
                        exc_info=True
                    )
                    # Send to DLQ
                    await self._send_to_dlq(message, str(e))

        except KafkaError as e:
            logger.error(f"Kafka error during consumption: {e}", exc_info=True)
            raise

        except Exception as e:
            logger.error(f"Error during consumption: {e}", exc_info=True)
            raise

    async def _send_to_dlq(self, message, error: str):
        """Send failed message to dead letter queue."""
        try:
            from app.kafka.producer import get_producer

            producer = await get_producer()

            dlq_message = {
                "original_topic": message.topic,
                "original_partition": message.partition,
                "original_offset": message.offset,
                "original_key": message.key,
                "original_value": message.value,
                "error": error,
                "consumer_group": self.group_id
            }

            await producer.publish(KafkaTopics.DLQ, dlq_message)
            logger.info(f"Message sent to DLQ from {message.topic}")

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}", exc_info=True)

    async def get_message_count(self, topic: str) -> int:
        """
        Get approximate message count in topic.

        Args:
            topic: Topic name

        Returns:
            Approximate message count
        """
        if not self.consumer:
            return 0

        try:
            partitions = self.consumer.partitions_for_topic(topic)
            if not partitions:
                return 0

            total = 0
            for partition in partitions:
                tp = (topic, partition)
                end_offset = await self.consumer.end_offsets([tp])
                beginning_offset = await self.consumer.beginning_offsets([tp])
                total += end_offset[tp] - beginning_offset[tp]

            return total

        except Exception as e:
            logger.error(f"Error getting message count: {e}", exc_info=True)
            return 0
