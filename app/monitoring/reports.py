"""Daily report generation."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

from app.db.connection import get_db_pool

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate daily reports and summaries."""

    @staticmethod
    async def generate_daily_report(
        report_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive daily report.

        Args:
            report_date: Date for report (defaults to yesterday)

        Returns:
            Dict with daily report data
        """
        try:
            # Default to yesterday
            if not report_date:
                report_date = datetime.now(timezone.utc) - timedelta(days=1)

            # Set date range for the day
            start_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            logger.info(f"Generating daily report for {start_date.date()}")

            # Verify database connectivity first
            db_pool = get_db_pool()

            # Gather all report sections
            tickets_summary = await ReportGenerator._get_tickets_summary(start_date, end_date)
            response_times = await ReportGenerator._get_response_times(start_date, end_date)
            escalations = await ReportGenerator._get_escalations_summary(start_date, end_date)
            sentiment = await ReportGenerator._get_sentiment_summary(start_date, end_date)
            tool_usage = await ReportGenerator._get_tool_usage_summary(start_date, end_date)
            errors = await ReportGenerator._get_error_summary(start_date, end_date)

            report = {
                "success": True,
                "report_date": start_date.date().isoformat(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "tickets_summary": tickets_summary,
                "response_times": response_times,
                "escalations": escalations,
                "sentiment": sentiment,
                "tool_usage": tool_usage,
                "errors": errors
            }

            logger.info(f"Daily report generated successfully for {start_date.date()}")
            return report

        except Exception as e:
            logger.error(f"Error generating daily report: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def _get_tickets_summary(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get tickets summary by channel."""
        try:
            db_pool = get_db_pool()

            # Get total tickets by channel from metrics
            result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'channel' as channel,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'response_time'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'channel'
                """,
                start_date,
                end_date
            )

            by_channel = {row["channel"]: row["count"] for row in result if row["channel"]}
            total = sum(by_channel.values())

            return {
                "total_tickets": total,
                "by_channel": by_channel
            }

        except Exception as e:
            logger.error(f"Error getting tickets summary: {e}", exc_info=True)
            return {
                "total_tickets": 0,
                "by_channel": {}
            }

    @staticmethod
    async def _get_response_times(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get average response times by channel."""
        try:
            db_pool = get_db_pool()

            result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'channel' as channel,
                    AVG(metric_value) as avg_response_time,
                    MIN(metric_value) as min_response_time,
                    MAX(metric_value) as max_response_time
                FROM agent_metrics
                WHERE metric_type = 'response_time'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'channel'
                """,
                start_date,
                end_date
            )

            by_channel = {}
            for row in result:
                if row["channel"]:
                    by_channel[row["channel"]] = {
                        "avg_ms": float(row["avg_response_time"]) if row["avg_response_time"] else 0,
                        "min_ms": float(row["min_response_time"]) if row["min_response_time"] else 0,
                        "max_ms": float(row["max_response_time"]) if row["max_response_time"] else 0
                    }

            # Calculate overall average
            overall_result = await db_pool.fetchrow(
                """
                SELECT AVG(metric_value) as avg_response_time
                FROM agent_metrics
                WHERE metric_type = 'response_time'
                AND recorded_at >= $1
                AND recorded_at < $2
                """,
                start_date,
                end_date
            )

            overall_avg = float(overall_result["avg_response_time"]) if overall_result["avg_response_time"] else 0

            return {
                "overall_avg_ms": overall_avg,
                "by_channel": by_channel
            }

        except Exception as e:
            logger.error(f"Error getting response times: {e}", exc_info=True)
            return {
                "overall_avg_ms": 0,
                "by_channel": {}
            }

    @staticmethod
    async def _get_escalations_summary(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get escalations summary."""
        try:
            db_pool = get_db_pool()

            # Total escalations
            total_result = await db_pool.fetchrow(
                """
                SELECT COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'escalation'
                AND recorded_at >= $1
                AND recorded_at < $2
                """,
                start_date,
                end_date
            )

            total_escalations = total_result["count"]

            # Escalations by channel
            channel_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'channel' as channel,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'escalation'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'channel'
                """,
                start_date,
                end_date
            )

            by_channel = {row["channel"]: row["count"] for row in channel_result if row["channel"]}

            # Escalations by reason
            reason_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'reason' as reason,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'escalation'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'reason'
                ORDER BY count DESC
                LIMIT 5
                """,
                start_date,
                end_date
            )

            by_reason = {row["reason"]: row["count"] for row in reason_result if row["reason"]}

            # Escalations by urgency
            urgency_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'urgency' as urgency,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'escalation'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'urgency'
                """,
                start_date,
                end_date
            )

            by_urgency = {row["urgency"]: row["count"] for row in urgency_result if row["urgency"]}

            return {
                "total_escalations": total_escalations,
                "by_channel": by_channel,
                "by_reason": by_reason,
                "by_urgency": by_urgency
            }

        except Exception as e:
            logger.error(f"Error getting escalations summary: {e}", exc_info=True)
            return {
                "total_escalations": 0,
                "by_channel": {},
                "by_reason": {},
                "by_urgency": {}
            }

    @staticmethod
    async def _get_sentiment_summary(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get sentiment analysis summary."""
        try:
            db_pool = get_db_pool()

            result = await db_pool.fetchrow(
                """
                SELECT
                    AVG(metric_value) as avg_sentiment,
                    MIN(metric_value) as min_sentiment,
                    MAX(metric_value) as max_sentiment,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'sentiment_score'
                AND recorded_at >= $1
                AND recorded_at < $2
                """,
                start_date,
                end_date
            )

            avg_sentiment = float(result["avg_sentiment"]) if result["avg_sentiment"] else 0
            min_sentiment = float(result["min_sentiment"]) if result["min_sentiment"] else 0
            max_sentiment = float(result["max_sentiment"]) if result["max_sentiment"] else 0
            count = result["count"]

            # Sentiment by channel
            channel_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'channel' as channel,
                    AVG(metric_value) as avg_sentiment
                FROM agent_metrics
                WHERE metric_type = 'sentiment_score'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'channel'
                """,
                start_date,
                end_date
            )

            by_channel = {
                row["channel"]: float(row["avg_sentiment"])
                for row in channel_result
                if row["channel"]
            }

            return {
                "avg_sentiment": avg_sentiment,
                "min_sentiment": min_sentiment,
                "max_sentiment": max_sentiment,
                "total_measurements": count,
                "by_channel": by_channel
            }

        except Exception as e:
            logger.error(f"Error getting sentiment summary: {e}", exc_info=True)
            return {
                "avg_sentiment": 0,
                "min_sentiment": 0,
                "max_sentiment": 0,
                "total_measurements": 0,
                "by_channel": {}
            }

    @staticmethod
    async def _get_tool_usage_summary(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get tool usage summary."""
        try:
            db_pool = get_db_pool()

            result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'tool_name' as tool_name,
                    COUNT(*) as count,
                    SUM(CASE WHEN (metadata->>'success')::boolean THEN 1 ELSE 0 END) as success_count
                FROM agent_metrics
                WHERE metric_type = 'tool_usage'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'tool_name'
                ORDER BY count DESC
                """,
                start_date,
                end_date
            )

            tools = {}
            for row in result:
                if row["tool_name"]:
                    tools[row["tool_name"]] = {
                        "total_uses": row["count"],
                        "successful_uses": row["success_count"],
                        "success_rate": row["success_count"] / row["count"] if row["count"] > 0 else 0
                    }

            return {
                "tools": tools,
                "total_tool_calls": sum(t["total_uses"] for t in tools.values())
            }

        except Exception as e:
            logger.error(f"Error getting tool usage summary: {e}", exc_info=True)
            return {
                "tools": {},
                "total_tool_calls": 0
            }

    @staticmethod
    async def _get_error_summary(
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get error summary."""
        try:
            db_pool = get_db_pool()

            # Total errors
            total_result = await db_pool.fetchrow(
                """
                SELECT COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'error'
                AND recorded_at >= $1
                AND recorded_at < $2
                """,
                start_date,
                end_date
            )

            total_errors = total_result["count"]

            # Errors by type
            type_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'error_type' as error_type,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'error'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'error_type'
                ORDER BY count DESC
                LIMIT 10
                """,
                start_date,
                end_date
            )

            by_type = {row["error_type"]: row["count"] for row in type_result if row["error_type"]}

            # Errors by channel
            channel_result = await db_pool.fetch(
                """
                SELECT
                    metadata->>'channel' as channel,
                    COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'error'
                AND recorded_at >= $1
                AND recorded_at < $2
                GROUP BY metadata->>'channel'
                """,
                start_date,
                end_date
            )

            by_channel = {row["channel"]: row["count"] for row in channel_result if row["channel"]}

            return {
                "total_errors": total_errors,
                "by_type": by_type,
                "by_channel": by_channel
            }

        except Exception as e:
            logger.error(f"Error getting error summary: {e}", exc_info=True)
            return {
                "total_errors": 0,
                "by_type": {},
                "by_channel": {}
            }

    @staticmethod
    async def get_resolution_rate(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate ticket resolution rate.

        Args:
            start_date: Optional start date
            end_date: Optional end date
            channel: Optional channel filter

        Returns:
            Dict with resolution rate data
        """
        try:
            # Default to last 24 hours
            if not end_date:
                end_date = datetime.now(timezone.utc)
            if not start_date:
                start_date = end_date - timedelta(days=1)

            db_pool = get_db_pool()

            # Count resolutions
            query = """
                SELECT COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'resolution_time'
                AND recorded_at >= $1
                AND recorded_at < $2
            """
            params = [start_date, end_date]

            if channel:
                query += " AND metadata->>'channel' = $3"
                params.append(channel)

            resolutions = await db_pool.fetchrow(query, *params)
            resolution_count = resolutions["count"]

            # Count total tickets (response_time is recorded for each ticket)
            query = """
                SELECT COUNT(*) as count
                FROM agent_metrics
                WHERE metric_type = 'response_time'
                AND recorded_at >= $1
                AND recorded_at < $2
            """
            params = [start_date, end_date]

            if channel:
                query += " AND metadata->>'channel' = $3"
                params.append(channel)

            tickets = await db_pool.fetchrow(query, *params)
            ticket_count = tickets["count"]

            # Calculate rate
            resolution_rate = resolution_count / ticket_count if ticket_count > 0 else 0

            return {
                "success": True,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "channel": channel,
                "total_tickets": ticket_count,
                "resolved_tickets": resolution_count,
                "resolution_rate": resolution_rate
            }

        except Exception as e:
            logger.error(f"Error calculating resolution rate: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
