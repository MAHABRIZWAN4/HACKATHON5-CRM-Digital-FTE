"""Tests for monitoring and metrics."""

import pytest
import pytest_asyncio
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.monitoring.logger import (
    JSONFormatter,
    setup_logging,
    get_logger,
    StructuredLogger
)
from app.monitoring.metrics import MetricsCollector
from app.monitoring.reports import ReportGenerator
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db


@pytest_asyncio.fixture
async def db_setup():
    """Setup database for monitoring tests."""
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


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_format_basic_log(self):
        """Test formatting basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test"
        record.funcName = "test_func"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test"
        assert log_data["function"] == "test_func"
        assert "timestamp" in log_data

    def test_format_with_context(self):
        """Test formatting log with context fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test"
        record.funcName = "test_func"
        record.channel = "gmail"
        record.ticket_id = "ticket_123"
        record.customer_id = "customer@example.com"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["channel"] == "gmail"
        assert log_data["ticket_id"] == "ticket_123"
        assert log_data["customer_id"] == "customer@example.com"

    def test_redact_sensitive_data(self):
        """Test sensitive data redaction."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test"
        record.funcName = "test_func"
        record.metadata = {
            "api_key": "secret123",
            "password": "mypassword",
            "normal_field": "normal_value"
        }

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["metadata"]["api_key"] == "[REDACTED]"
        assert log_data["metadata"]["password"] == "[REDACTED]"
        assert log_data["metadata"]["normal_field"] == "normal_value"

    def test_format_with_exception(self):
        """Test formatting log with exception."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.module = "test"
        record.funcName = "test_func"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "ERROR"
        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]


class TestLoggingSetup:
    """Test logging setup."""

    def test_setup_logging_creates_directory(self, tmp_path):
        """Test that setup_logging creates log directory."""
        log_dir = tmp_path / "logs"
        setup_logging(log_level="INFO", log_dir=str(log_dir), component="test")

        assert log_dir.exists()
        assert (log_dir / "test.log").exists()
        assert (log_dir / "test_errors.log").exists()

    def test_setup_logging_sets_level(self, tmp_path):
        """Test that setup_logging sets correct log level."""
        log_dir = tmp_path / "logs"
        setup_logging(log_level="DEBUG", log_dir=str(log_dir), component="test")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_get_logger_with_context(self):
        """Test getting logger with context."""
        logger = get_logger(
            "test",
            channel="gmail",
            ticket_id="ticket_123",
            customer_id="customer@example.com"
        )

        assert logger.extra["channel"] == "gmail"
        assert logger.extra["ticket_id"] == "ticket_123"
        assert logger.extra["customer_id"] == "customer@example.com"


class TestStructuredLogger:
    """Test structured logger."""

    def test_structured_logger_initialization(self):
        """Test structured logger initialization."""
        logger = StructuredLogger(
            "test",
            channel="gmail",
            ticket_id="ticket_123"
        )

        assert logger.logger is not None

    def test_log_ticket_event(self, caplog):
        """Test logging ticket event."""
        logger = StructuredLogger("test")

        with caplog.at_level(logging.INFO):
            logger.log_ticket_event("created", "ticket_123", "open")

        assert "Ticket created: ticket_123" in caplog.text

    def test_log_escalation(self, caplog):
        """Test logging escalation."""
        logger = StructuredLogger("test")

        with caplog.at_level(logging.WARNING):
            logger.log_escalation("ticket_123", "Customer requested human", "high")

        assert "Ticket escalated: ticket_123" in caplog.text

    def test_log_metric(self, caplog):
        """Test logging metric."""
        logger = StructuredLogger("test")

        with caplog.at_level(logging.INFO):
            logger.log_metric("response_time", 150.5)

        assert "Metric: response_time = 150.5" in caplog.text


class TestMetricsCollection:
    """Test metrics collection."""

    @pytest.mark.asyncio
    async def test_record_response_time(self, db_setup):
        """Test recording response time metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_response_time(
                channel="gmail",
                response_time_ms=150.5,
                ticket_id="ticket_123"
            )

            assert result["success"] is True
            assert result["metric_type"] == "response_time"
            assert result["value"] == 150.5
            mock_producer.publish_metric.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_resolution(self, db_setup):
        """Test recording resolution metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_resolution(
                ticket_id="ticket_123",
                resolution_time_hours=2.5,
                channel="gmail"
            )

            assert result["success"] is True
            assert result["metric_type"] == "resolution_time"
            assert result["value"] == 2.5

    @pytest.mark.asyncio
    async def test_record_escalation(self, db_setup):
        """Test recording escalation metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_escalation(
                ticket_id="ticket_123",
                channel="gmail",
                reason="Customer requested human",
                urgency="high"
            )

            assert result["success"] is True
            assert result["metric_type"] == "escalation"

    @pytest.mark.asyncio
    async def test_record_sentiment(self, db_setup):
        """Test recording sentiment metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_sentiment(
                ticket_id="ticket_123",
                sentiment_score=0.75,
                channel="gmail"
            )

            assert result["success"] is True
            assert result["metric_type"] == "sentiment_score"
            assert result["value"] == 0.75

    @pytest.mark.asyncio
    async def test_record_tool_usage(self, db_setup):
        """Test recording tool usage metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_tool_usage(
                tool_name="search_knowledge_base",
                ticket_id="ticket_123",
                success=True
            )

            assert result["success"] is True
            assert result["metric_type"] == "tool_usage"
            assert result["tool_name"] == "search_knowledge_base"

    @pytest.mark.asyncio
    async def test_record_error(self, db_setup):
        """Test recording error metric."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_error(
                error_type="DatabaseError",
                error_message="Connection failed",
                channel="gmail",
                ticket_id="ticket_123"
            )

            assert result["success"] is True
            assert result["metric_type"] == "error"

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, db_setup):
        """Test getting metrics summary."""
        # First record some metrics
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            await MetricsCollector.record_response_time("gmail", 100.0)
            await MetricsCollector.record_response_time("gmail", 200.0)

        # Get summary
        result = await MetricsCollector.get_metrics_summary(
            metric_type="response_time",
            channel="gmail"
        )

        assert result["success"] is True
        assert result["metric_type"] == "response_time"
        assert result["count"] >= 0


class TestKafkaMetricsPublishing:
    """Test Kafka metrics publishing."""

    @pytest.mark.asyncio
    async def test_metrics_published_to_kafka(self, db_setup):
        """Test that metrics are published to Kafka."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            await MetricsCollector.record_response_time(
                channel="gmail",
                response_time_ms=150.5
            )

            # Verify Kafka publish was called
            mock_producer.publish_metric.assert_called_once()
            call_args = mock_producer.publish_metric.call_args[0][0]
            assert call_args["metric_type"] == "response_time"
            assert call_args["metric_value"] == 150.5
            assert call_args["channel"] == "gmail"

    @pytest.mark.asyncio
    async def test_kafka_publish_failure_handled(self, db_setup):
        """Test that Kafka publish failures are handled gracefully."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(side_effect=Exception("Kafka error"))
            mock_get_producer.return_value = mock_producer

            # Should still succeed even if Kafka fails
            result = await MetricsCollector.record_response_time(
                channel="gmail",
                response_time_ms=150.5
            )

            # The metric recording itself should succeed (database write)
            # even if Kafka publish fails
            assert "metric_id" in result or "error" in result


class TestDailyReports:
    """Test daily report generation."""

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, db_setup):
        """Test generating daily report."""
        report_date = datetime.now(timezone.utc) - timedelta(days=1)
        result = await ReportGenerator.generate_daily_report(report_date)

        assert result["success"] is True
        assert "report_date" in result
        assert "tickets_summary" in result
        assert "response_times" in result
        assert "escalations" in result
        assert "sentiment" in result
        assert "tool_usage" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_daily_report_structure(self, db_setup):
        """Test daily report has correct structure."""
        result = await ReportGenerator.generate_daily_report()

        assert result["success"] is True

        # Check tickets summary structure
        tickets = result["tickets_summary"]
        assert "total_tickets" in tickets
        assert "by_channel" in tickets

        # Check response times structure
        response_times = result["response_times"]
        assert "overall_avg_ms" in response_times
        assert "by_channel" in response_times

        # Check escalations structure
        escalations = result["escalations"]
        assert "total_escalations" in escalations
        assert "by_channel" in escalations
        assert "by_reason" in escalations
        assert "by_urgency" in escalations

        # Check sentiment structure
        sentiment = result["sentiment"]
        assert "avg_sentiment" in sentiment
        assert "by_channel" in sentiment

        # Check tool usage structure
        tool_usage = result["tool_usage"]
        assert "tools" in tool_usage
        assert "total_tool_calls" in tool_usage

        # Check errors structure
        errors = result["errors"]
        assert "total_errors" in errors
        assert "by_type" in errors
        assert "by_channel" in errors

    @pytest.mark.asyncio
    async def test_get_resolution_rate(self, db_setup):
        """Test calculating resolution rate."""
        result = await ReportGenerator.get_resolution_rate()

        assert result["success"] is True
        assert "total_tickets" in result
        assert "resolved_tickets" in result
        assert "resolution_rate" in result
        assert 0 <= result["resolution_rate"] <= 1

    @pytest.mark.asyncio
    async def test_resolution_rate_by_channel(self, db_setup):
        """Test calculating resolution rate by channel."""
        result = await ReportGenerator.get_resolution_rate(channel="gmail")

        assert result["success"] is True
        assert result["channel"] == "gmail"


class TestErrorHandling:
    """Test error handling in monitoring."""

    @pytest.mark.asyncio
    async def test_metrics_handles_database_error(self, db_setup):
        """Test metrics collection handles database errors."""
        with patch('app.monitoring.metrics.get_db_pool') as mock_pool:
            mock_pool.side_effect = Exception("Database error")

            result = await MetricsCollector.record_response_time(
                channel="gmail",
                response_time_ms=150.5
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_report_handles_database_error(self, db_setup):
        """Test report generation handles database errors."""
        with patch('app.monitoring.reports.get_db_pool') as mock_pool:
            mock_pool.side_effect = Exception("Database error")

            result = await ReportGenerator.generate_daily_report()

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_metrics_summary_handles_error(self, db_setup):
        """Test metrics summary handles errors."""
        with patch('app.monitoring.metrics.get_db_pool') as mock_pool:
            mock_pool.side_effect = Exception("Database error")

            result = await MetricsCollector.get_metrics_summary("response_time")

            assert result["success"] is False
            assert "error" in result


class TestMetricsIntegration:
    """Test metrics integration with other components."""

    @pytest.mark.asyncio
    async def test_metrics_stored_in_database(self, db_setup):
        """Test that metrics are stored in database."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            result = await MetricsCollector.record_response_time(
                channel="gmail",
                response_time_ms=150.5,
                ticket_id="ticket_123"
            )

            assert result["success"] is True
            assert "metric_id" in result

            # Verify metric can be retrieved
            summary = await MetricsCollector.get_metrics_summary("response_time")
            assert summary["success"] is True

    @pytest.mark.asyncio
    async def test_multiple_metrics_recorded(self, db_setup):
        """Test recording multiple different metrics."""
        with patch('app.monitoring.metrics.get_producer') as mock_get_producer:
            mock_producer = AsyncMock()
            mock_producer.publish_metric = AsyncMock(return_value=True)
            mock_get_producer.return_value = mock_producer

            # Record different types of metrics
            result1 = await MetricsCollector.record_response_time("gmail", 100.0)
            result2 = await MetricsCollector.record_sentiment("ticket_123", 0.8, "gmail")
            result3 = await MetricsCollector.record_tool_usage("search_knowledge_base")

            assert result1["success"] is True
            assert result2["success"] is True
            assert result3["success"] is True
