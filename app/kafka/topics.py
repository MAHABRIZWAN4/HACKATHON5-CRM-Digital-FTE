"""Kafka topic definitions."""

import os


class KafkaTopics:
    """Kafka topic names."""

    # Main incoming tickets topic (all channels)
    TICKETS_INCOMING = os.getenv("KAFKA_TOPIC_TICKETS_INCOMING", "fte.tickets.incoming")

    # Channel-specific inbound topics
    EMAIL_INBOUND = os.getenv("KAFKA_TOPIC_EMAIL_INBOUND", "fte.channels.email.inbound")
    WHATSAPP_INBOUND = os.getenv("KAFKA_TOPIC_WHATSAPP_INBOUND", "fte.channels.whatsapp.inbound")
    WEBFORM_INBOUND = os.getenv("KAFKA_TOPIC_WEBFORM_INBOUND", "fte.channels.webform.inbound")

    # Escalations topic
    ESCALATIONS = os.getenv("KAFKA_TOPIC_ESCALATIONS", "fte.escalations")

    # Metrics topic
    METRICS = os.getenv("KAFKA_TOPIC_METRICS", "fte.metrics")

    # Dead letter queue
    DLQ = os.getenv("KAFKA_TOPIC_DLQ", "fte.dlq")

    @classmethod
    def get_all_topics(cls) -> list:
        """Get list of all topics."""
        return [
            cls.TICKETS_INCOMING,
            cls.EMAIL_INBOUND,
            cls.WHATSAPP_INBOUND,
            cls.WEBFORM_INBOUND,
            cls.ESCALATIONS,
            cls.METRICS,
            cls.DLQ
        ]

    @classmethod
    def get_channel_topic(cls, channel: str) -> str:
        """Get topic for specific channel."""
        channel_map = {
            "gmail": cls.EMAIL_INBOUND,
            "whatsapp": cls.WHATSAPP_INBOUND,
            "web_form": cls.WEBFORM_INBOUND
        }
        return channel_map.get(channel, cls.TICKETS_INCOMING)
