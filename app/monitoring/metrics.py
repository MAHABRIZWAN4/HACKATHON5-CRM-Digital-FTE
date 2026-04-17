"""Metrics collection and tracking."""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.db.connection import get_db_pool
from app.kafka.producer import get_producer
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and store application metrics."""

    @staticmethod
    async def record_response_time(
        channel: str,
        response_time_ms: float,
        ticket_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record response time metric.

        Args:
            channel: Channel name (gmail, whatsapp, web_form)
            response_time_ms: Response time in milliseconds
            ticket_id: Optional ticket ID (must be valid UUID or None)
            conversation_id: Optional conversation ID
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.info(f"Recording response time: {response_time_ms}ms for {channel}")

            # Store in database
            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata["channel"] = channel

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    # Try to parse as UUID
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    # Not a valid UUID, store in metadata instead
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "response_time",
                response_time_ms,
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "response_time",
                "metric_value": response_time_ms,
                "channel": channel,
                "ticket_id": ticket_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "response_time",
                "value": response_time_ms
            }

        except Exception as e:
            logger.error(f"Error recording response time: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def record_resolution(
        ticket_id: str,
        resolution_time_hours: float,
        channel: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record ticket resolution metric.

        Args:
            ticket_id: Ticket ID (must be valid UUID or None)
            resolution_time_hours: Time to resolve in hours
            channel: Channel name
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.info(f"Recording resolution: {ticket_id} in {resolution_time_hours}h")

            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata["channel"] = channel

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "resolution_time",
                resolution_time_hours,
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "resolution_time",
                "metric_value": resolution_time_hours,
                "ticket_id": ticket_id,
                "channel": channel,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "resolution_time",
                "value": resolution_time_hours
            }

        except Exception as e:
            logger.error(f"Error recording resolution: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def record_escalation(
        ticket_id: str,
        channel: str,
        reason: str,
        urgency: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record escalation metric.

        Args:
            ticket_id: Ticket ID (must be valid UUID or None)
            channel: Channel name
            reason: Escalation reason
            urgency: Urgency level
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.info(f"Recording escalation: {ticket_id}")

            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata.update({
                "channel": channel,
                "reason": reason,
                "urgency": urgency
            })

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "escalation",
                1.0,  # Count as 1 escalation
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "escalation",
                "ticket_id": ticket_id,
                "channel": channel,
                "reason": reason,
                "urgency": urgency,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "escalation"
            }

        except Exception as e:
            logger.error(f"Error recording escalation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def record_sentiment(
        ticket_id: str,
        sentiment_score: float,
        channel: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record customer sentiment metric.

        Args:
            ticket_id: Ticket ID (must be valid UUID or None)
            sentiment_score: Sentiment score (0-1)
            channel: Channel name
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.info(f"Recording sentiment: {sentiment_score} for {ticket_id}")

            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata["channel"] = channel

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "sentiment_score",
                sentiment_score,
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "sentiment_score",
                "metric_value": sentiment_score,
                "ticket_id": ticket_id,
                "channel": channel,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "sentiment_score",
                "value": sentiment_score
            }

        except Exception as e:
            logger.error(f"Error recording sentiment: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def record_tool_usage(
        tool_name: str,
        ticket_id: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record agent tool usage metric.

        Args:
            tool_name: Name of the tool used
            ticket_id: Optional ticket ID (must be valid UUID or None)
            success: Whether tool execution was successful
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.info(f"Recording tool usage: {tool_name}")

            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata.update({
                "tool_name": tool_name,
                "success": success
            })

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "tool_usage",
                1.0,  # Count as 1 usage
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "tool_usage",
                "tool_name": tool_name,
                "ticket_id": ticket_id,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "tool_usage",
                "tool_name": tool_name
            }

        except Exception as e:
            logger.error(f"Error recording tool usage: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def record_error(
        error_type: str,
        error_message: str,
        channel: Optional[str] = None,
        ticket_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record error metric.

        Args:
            error_type: Type of error
            error_message: Error message
            channel: Optional channel name
            ticket_id: Optional ticket ID (must be valid UUID or None)
            metadata: Optional additional metadata

        Returns:
            Dict with recording result
        """
        try:
            logger.error(f"Recording error: {error_type} - {error_message}")

            db_pool = get_db_pool()
            metric_id = str(uuid4())

            metric_metadata = metadata or {}
            metric_metadata.update({
                "error_type": error_type,
                "error_message": error_message
            })
            if channel:
                metric_metadata["channel"] = channel

            # Validate ticket_id is UUID format or set to None
            db_ticket_id = None
            if ticket_id:
                try:
                    from uuid import UUID
                    UUID(ticket_id)
                    db_ticket_id = ticket_id
                except (ValueError, AttributeError):
                    metric_metadata["ticket_id_string"] = ticket_id

            await db_pool.execute(
                """
                INSERT INTO agent_metrics (id, metric_type, metric_value, ticket_id, metadata, recorded_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                metric_id,
                "error",
                1.0,  # Count as 1 error
                db_ticket_id,
                json.dumps(metric_metadata),
                datetime.now(timezone.utc)
            )

            # Publish to Kafka
            producer = await get_producer()
            await producer.publish_metric({
                "metric_id": metric_id,
                "metric_type": "error",
                "error_type": error_type,
                "error_message": error_message,
                "channel": channel,
                "ticket_id": ticket_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "metric_id": metric_id,
                "metric_type": "error"
            }

        except Exception as e:
            logger.error(f"Error recording error metric: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def get_metrics_summary(
        metric_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of metrics.

        Args:
            metric_type: Type of metric
            start_date: Optional start date
            end_date: Optional end date
            channel: Optional channel filter

        Returns:
            Dict with metrics summary
        """
        try:
            db_pool = get_db_pool()

            # Default to last 24 hours if no dates provided
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(days=1)

            # Build query
            query = """
                SELECT
                    COUNT(*) as count,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value
                FROM agent_metrics
                WHERE metric_type = $1
                AND recorded_at >= $2
                AND recorded_at <= $3
            """
            params = [metric_type, start_date, end_date]

            if channel:
                query += " AND metadata->>'channel' = $4"
                params.append(channel)

            result = await db_pool.fetchrow(query, *params)

            return {
                "success": True,
                "metric_type": metric_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "channel": channel,
                "count": result["count"],
                "avg_value": float(result["avg_value"]) if result["avg_value"] else 0,
                "min_value": float(result["min_value"]) if result["min_value"] else 0,
                "max_value": float(result["max_value"]) if result["max_value"] else 0
            }

        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
