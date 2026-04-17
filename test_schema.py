"""
Pytest tests for PostgreSQL CRM schema validation.
Tests all tables, columns, indexes, UUID primary keys, and timestamps.
"""

import pytest
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from typing import List, Dict


# Database connection parameters
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "database": os.getenv("DB_NAME", "customer_success_test"),
}


@pytest.fixture(scope="module")
def db_connection():
    """Create test database and apply schema."""
    # Connect to postgres database to create test database
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Drop and recreate test database
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_CONFIG['database']}")
    cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
    cursor.close()
    conn.close()

    # Connect to test database
    test_conn = psycopg2.connect(**DB_CONFIG)
    test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    # Apply schema
    with open("schema.sql", "r") as f:
        schema_sql = f.read()

    cursor = test_conn.cursor()
    cursor.execute(schema_sql)
    cursor.close()

    yield test_conn

    # Cleanup
    test_conn.close()

    # Drop test database
    conn = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_CONFIG['database']}")
    cursor.close()
    conn.close()


def get_tables(cursor) -> List[str]:
    """Get all table names in the database."""
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    return [row[0] for row in cursor.fetchall()]


def get_columns(cursor, table_name: str) -> List[Dict]:
    """Get column information for a table."""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))

    columns = []
    for row in cursor.fetchall():
        columns.append({
            "name": row[0],
            "type": row[1],
            "nullable": row[2] == "YES",
            "default": row[3],
        })
    return columns


def get_indexes(cursor, table_name: str) -> List[str]:
    """Get index names for a table."""
    cursor.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s
    """, (table_name,))
    return [row[0] for row in cursor.fetchall()]


class TestSchemaTablesExist:
    """Test that all required tables exist."""

    def test_all_tables_exist(self, db_connection):
        """Verify all 8 required tables are created."""
        cursor = db_connection.cursor()
        tables = get_tables(cursor)
        cursor.close()

        required_tables = [
            "customers",
            "customer_identifiers",
            "conversations",
            "messages",
            "tickets",
            "knowledge_base",
            "channel_configs",
            "agent_metrics",
        ]

        for table in required_tables:
            assert table in tables, f"Table '{table}' does not exist"

        assert len(tables) == len(required_tables), f"Expected {len(required_tables)} tables, found {len(tables)}"


class TestSchemaColumns:
    """Test that all tables have correct columns."""

    def test_customers_columns(self, db_connection):
        """Verify customers table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "customers")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
        assert "phone" in column_names
        assert "company" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

        # Check metadata is JSONB
        metadata_col = next(col for col in columns if col["name"] == "metadata")
        assert metadata_col["type"] == "jsonb"

    def test_customer_identifiers_columns(self, db_connection):
        """Verify customer_identifiers table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "customer_identifiers")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "customer_id" in column_names
        assert "channel" in column_names
        assert "identifier" in column_names
        assert "verified" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_conversations_columns(self, db_connection):
        """Verify conversations table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "conversations")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "customer_id" in column_names
        assert "channel" in column_names
        assert "status" in column_names
        assert "subject" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names
        assert "closed_at" in column_names

    def test_messages_columns(self, db_connection):
        """Verify messages table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "messages")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "conversation_id" in column_names
        assert "sender_type" in column_names
        assert "sender_id" in column_names
        assert "content" in column_names
        assert "channel_message_id" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names

    def test_tickets_columns(self, db_connection):
        """Verify tickets table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "tickets")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "conversation_id" in column_names
        assert "customer_id" in column_names
        assert "title" in column_names
        assert "description" in column_names
        assert "status" in column_names
        assert "priority" in column_names
        assert "category" in column_names
        assert "assigned_to" in column_names
        assert "escalated" in column_names
        assert "escalated_at" in column_names
        assert "resolved_at" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_knowledge_base_columns(self, db_connection):
        """Verify knowledge_base table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "knowledge_base")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "title" in column_names
        assert "content" in column_names
        assert "category" in column_names
        assert "tags" in column_names
        assert "embedding" in column_names
        assert "metadata" in column_names
        assert "active" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_channel_configs_columns(self, db_connection):
        """Verify channel_configs table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "channel_configs")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "channel" in column_names
        assert "enabled" in column_names
        assert "config" in column_names
        assert "credentials" in column_names
        assert "metadata" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_agent_metrics_columns(self, db_connection):
        """Verify agent_metrics table columns."""
        cursor = db_connection.cursor()
        columns = get_columns(cursor, "agent_metrics")
        cursor.close()

        column_names = [col["name"] for col in columns]

        assert "id" in column_names
        assert "metric_type" in column_names
        assert "metric_value" in column_names
        assert "conversation_id" in column_names
        assert "ticket_id" in column_names
        assert "metadata" in column_names
        assert "recorded_at" in column_names


class TestSchemaIndexes:
    """Test that all required indexes are created."""

    def test_customers_indexes(self, db_connection):
        """Verify customers table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "customers")
        cursor.close()

        assert "customers_pkey" in indexes  # Primary key
        assert "idx_customers_email" in indexes
        assert "idx_customers_phone" in indexes
        assert "idx_customers_created_at" in indexes

    def test_customer_identifiers_indexes(self, db_connection):
        """Verify customer_identifiers table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "customer_identifiers")
        cursor.close()

        assert "customer_identifiers_pkey" in indexes
        assert "idx_customer_identifiers_customer_id" in indexes
        assert "idx_customer_identifiers_channel" in indexes
        assert "idx_customer_identifiers_identifier" in indexes

    def test_conversations_indexes(self, db_connection):
        """Verify conversations table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "conversations")
        cursor.close()

        assert "conversations_pkey" in indexes
        assert "idx_conversations_customer_id" in indexes
        assert "idx_conversations_channel" in indexes
        assert "idx_conversations_status" in indexes
        assert "idx_conversations_created_at" in indexes

    def test_messages_indexes(self, db_connection):
        """Verify messages table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "messages")
        cursor.close()

        assert "messages_pkey" in indexes
        assert "idx_messages_conversation_id" in indexes
        assert "idx_messages_sender_type" in indexes
        assert "idx_messages_created_at" in indexes
        assert "idx_messages_channel_message_id" in indexes

    def test_tickets_indexes(self, db_connection):
        """Verify tickets table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "tickets")
        cursor.close()

        assert "tickets_pkey" in indexes
        assert "idx_tickets_conversation_id" in indexes
        assert "idx_tickets_customer_id" in indexes
        assert "idx_tickets_status" in indexes
        assert "idx_tickets_priority" in indexes
        assert "idx_tickets_escalated" in indexes
        assert "idx_tickets_created_at" in indexes

    def test_knowledge_base_indexes(self, db_connection):
        """Verify knowledge_base table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "knowledge_base")
        cursor.close()

        assert "knowledge_base_pkey" in indexes
        assert "idx_knowledge_base_category" in indexes
        assert "idx_knowledge_base_active" in indexes
        # assert "idx_knowledge_base_embedding" in indexes  # Disabled until pgvector is installed

    def test_channel_configs_indexes(self, db_connection):
        """Verify channel_configs table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "channel_configs")
        cursor.close()

        assert "channel_configs_pkey" in indexes
        assert "idx_channel_configs_channel" in indexes
        assert "idx_channel_configs_enabled" in indexes

    def test_agent_metrics_indexes(self, db_connection):
        """Verify agent_metrics table indexes."""
        cursor = db_connection.cursor()
        indexes = get_indexes(cursor, "agent_metrics")
        cursor.close()

        assert "agent_metrics_pkey" in indexes
        assert "idx_agent_metrics_metric_type" in indexes
        assert "idx_agent_metrics_conversation_id" in indexes
        assert "idx_agent_metrics_ticket_id" in indexes
        assert "idx_agent_metrics_recorded_at" in indexes


class TestUUIDPrimaryKeys:
    """Test that UUID primary keys work correctly."""

    def test_customers_uuid_pk(self, db_connection):
        """Test UUID primary key generation for customers."""
        cursor = db_connection.cursor()

        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id
        """)
        customer_id = cursor.fetchone()[0]

        # Verify it's a valid UUID format
        assert len(str(customer_id)) == 36
        assert str(customer_id).count("-") == 4

        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()

    def test_conversations_uuid_pk(self, db_connection):
        """Test UUID primary key generation for conversations."""
        cursor = db_connection.cursor()

        # Create customer first
        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id
        """)
        customer_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO conversations (customer_id, channel, status)
            VALUES (%s, 'web', 'active')
            RETURNING id
        """, (customer_id,))
        conversation_id = cursor.fetchone()[0]

        # Verify it's a valid UUID format
        assert len(str(conversation_id)) == 36
        assert str(conversation_id).count("-") == 4

        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()

    def test_tickets_uuid_pk(self, db_connection):
        """Test UUID primary key generation for tickets."""
        cursor = db_connection.cursor()

        # Create customer and conversation first
        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id
        """)
        customer_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO conversations (customer_id, channel, status)
            VALUES (%s, 'web', 'active')
            RETURNING id
        """, (customer_id,))
        conversation_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO tickets (conversation_id, customer_id, title, status, priority)
            VALUES (%s, %s, 'Test Ticket', 'open', 'medium')
            RETURNING id
        """, (conversation_id, customer_id))
        ticket_id = cursor.fetchone()[0]

        # Verify it's a valid UUID format
        assert len(str(ticket_id)) == 36
        assert str(ticket_id).count("-") == 4

        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()


class TestTimestampsWithTimezone:
    """Test that timestamps with timezone work correctly."""

    def test_customers_timestamps(self, db_connection):
        """Test created_at and updated_at timestamps for customers."""
        cursor = db_connection.cursor()

        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id, created_at, updated_at
        """)
        customer_id, created_at, updated_at = cursor.fetchone()

        # Verify timestamps are set
        assert created_at is not None
        assert updated_at is not None

        # Verify they're timezone-aware (psycopg2 returns datetime with tzinfo)
        assert created_at.tzinfo is not None
        assert updated_at.tzinfo is not None

        # Update and verify updated_at changes
        import time
        time.sleep(0.1)  # Small delay to ensure timestamp difference

        cursor.execute("""
            UPDATE customers SET name = 'Updated Customer' WHERE id = %s
            RETURNING updated_at
        """, (customer_id,))
        new_updated_at = cursor.fetchone()[0]

        assert new_updated_at > updated_at

        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()

    def test_conversations_timestamps(self, db_connection):
        """Test timestamps for conversations."""
        cursor = db_connection.cursor()

        # Create customer first
        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id
        """)
        customer_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO conversations (customer_id, channel, status)
            VALUES (%s, 'web', 'active')
            RETURNING id, created_at, updated_at
        """, (customer_id,))
        conversation_id, created_at, updated_at = cursor.fetchone()

        # Verify timestamps are timezone-aware
        assert created_at.tzinfo is not None
        assert updated_at.tzinfo is not None

        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()

    def test_messages_timestamps(self, db_connection):
        """Test created_at timestamp for messages."""
        cursor = db_connection.cursor()

        # Create customer and conversation first
        cursor.execute("""
            INSERT INTO customers (name, email)
            VALUES ('Test Customer', 'test@example.com')
            RETURNING id
        """)
        customer_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO conversations (customer_id, channel, status)
            VALUES (%s, 'web', 'active')
            RETURNING id
        """, (customer_id,))
        conversation_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO messages (conversation_id, sender_type, content)
            VALUES (%s, 'customer', 'Test message')
            RETURNING id, created_at
        """, (conversation_id,))
        message_id, created_at = cursor.fetchone()

        # Verify timestamp is timezone-aware
        assert created_at.tzinfo is not None

        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        cursor.close()

    def test_agent_metrics_timestamps(self, db_connection):
        """Test recorded_at timestamp for agent_metrics."""
        cursor = db_connection.cursor()

        cursor.execute("""
            INSERT INTO agent_metrics (metric_type, metric_value)
            VALUES ('response_time', 1.5)
            RETURNING id, recorded_at
        """)
        metric_id, recorded_at = cursor.fetchone()

        # Verify timestamp is timezone-aware
        assert recorded_at.tzinfo is not None

        cursor.execute("DELETE FROM agent_metrics WHERE id = %s", (metric_id,))
        cursor.close()
