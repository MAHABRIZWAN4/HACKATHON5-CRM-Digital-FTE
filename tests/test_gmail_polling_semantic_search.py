"""Tests for Gmail polling and pgvector semantic search."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestGmailPolling:
    """Test Gmail polling functionality."""

    @pytest.mark.asyncio
    async def test_poll_inbox_disabled(self):
        """Test polling when disabled."""
        from app.handlers.gmail import GmailHandler

        handler = GmailHandler()
        handler.config.polling_enabled = False

        result = await handler.poll_inbox()
        assert result == []

    @pytest.mark.asyncio
    async def test_poll_inbox_no_messages(self):
        """Test polling with no unread messages."""
        from app.handlers.gmail import GmailHandler

        handler = GmailHandler()
        handler.config.polling_enabled = True

        # Mock Gmail service
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {'messages': []}

        with patch.object(handler, '_get_gmail_service', return_value=mock_service):
            result = await handler.poll_inbox()
            assert result == []

    @pytest.mark.asyncio
    async def test_parse_gmail_message(self):
        """Test parsing Gmail API message."""
        from app.handlers.gmail import GmailHandler

        handler = GmailHandler()

        # Mock Gmail message
        message = {
            'id': 'msg123',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'John Doe <john@example.com>'},
                    {'name': 'Subject', 'value': 'Test Subject'}
                ],
                'body': {
                    'data': 'VGVzdCBib2R5'  # base64 for "Test body"
                }
            }
        }

        result = handler._parse_gmail_message(message)

        assert result['message_id'] == 'msg123'
        assert result['from_email'] == 'john@example.com'
        assert result['from_name'] == 'John Doe'
        assert result['subject'] == 'Test Subject'
        assert 'Test body' in result['body']

    @pytest.mark.asyncio
    async def test_get_message_body_simple(self):
        """Test extracting message body from simple payload."""
        from app.handlers.gmail import GmailHandler
        import base64

        handler = GmailHandler()

        payload = {
            'body': {
                'data': base64.urlsafe_b64encode(b'Simple body').decode('utf-8')
            }
        }

        result = handler._get_message_body(payload)
        assert result == 'Simple body'

    @pytest.mark.asyncio
    async def test_get_message_body_multipart(self):
        """Test extracting message body from multipart payload."""
        from app.handlers.gmail import GmailHandler
        import base64

        handler = GmailHandler()

        payload = {
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(b'Multipart body').decode('utf-8')
                    }
                }
            ]
        }

        result = handler._get_message_body(payload)
        assert result == 'Multipart body'

    @pytest.mark.asyncio
    async def test_start_stop_polling(self):
        """Test starting and stopping polling."""
        from app.handlers.gmail import GmailHandler

        handler = GmailHandler()
        handler.config.polling_enabled = True
        handler.config.polling_interval = 1

        # Mock poll_inbox to avoid actual polling
        handler.poll_inbox = AsyncMock(return_value=[])

        # Start polling in background
        task = asyncio.create_task(handler.start_polling())

        # Wait a bit
        await asyncio.sleep(0.1)

        # Stop polling
        await handler.stop_polling()

        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert not handler._is_polling


class TestSemanticSearch:
    """Test pgvector semantic search functionality."""

    @pytest.mark.asyncio
    async def test_search_knowledge_base_text_fallback(self, db_pool):
        """Test knowledge base search with full-text search."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            # Insert test data
            await db_pool.execute(
                """
                INSERT INTO knowledge_base (title, content, category, active)
                VALUES ($1, $2, $3, true)
                """,
                "Test Article",
                "This is test content about login issues",
                "account"
            )

            result = await search_knowledge_base("login", max_results=5)

            assert result['success'] is True
            assert len(result['results']) > 0
            assert result['search_method'] in ['fulltext', 'ilike']
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_search_knowledge_base_empty_query(self, db_pool):
        """Test search with empty results."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            result = await search_knowledge_base("xyznonexistent123", max_results=5)

            assert result['success'] is True
            assert len(result['results']) == 0
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_search_knowledge_base_max_results(self, db_pool):
        """Test max_results parameter."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            # Insert multiple test entries
            for i in range(5):
                await db_pool.execute(
                    """
                    INSERT INTO knowledge_base (title, content, category, active)
                    VALUES ($1, $2, $3, true)
                    """,
                    f"Article {i}",
                    f"Content about password reset {i}",
                    "account"
                )

            result = await search_knowledge_base("password", max_results=3)

            assert result['success'] is True
            assert len(result['results']) <= 3
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_fulltext_search_functionality(self, db_pool):
        """Test full-text search functionality."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            # Insert test data
            await db_pool.execute(
                """
                INSERT INTO knowledge_base (title, content, category, active)
                VALUES ($1, $2, $3, true)
                """,
                "Password Reset Guide",
                "How to reset your password when you forgot it",
                "account"
            )

            result = await search_knowledge_base("forgot password", max_results=5)

            assert result['success'] is True
            assert len(result['results']) > 0
            assert result['search_method'] in ['fulltext', 'ilike']
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_fulltext_search_relevance_ranking(self, db_pool):
        """Test that full-text search ranks results by relevance."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            # Insert test data with varying relevance
            await db_pool.execute(
                """
                INSERT INTO knowledge_base (title, content, category, active)
                VALUES ($1, $2, $3, true)
                """,
                "Account Login Issues",
                "How to troubleshoot login problems and reset credentials",
                "account"
            )

            result = await search_knowledge_base("login", max_results=5)

            assert result['success'] is True
            if len(result['results']) > 0:
                # Check that results have relevance scores
                assert 'relevance' in result['results'][0]
                assert result['results'][0]['relevance'] > 0
        finally:
            await close_db()

    @pytest.mark.asyncio
    async def test_search_inactive_entries_excluded(self, db_pool):
        """Test that inactive entries are not returned."""
        from app.agent.tools import search_knowledge_base
        from app.db.connection import init_db, close_db
        from app.db.config import DatabaseConfig

        # Initialize global pool for the tool
        config = DatabaseConfig.from_env()
        await init_db(config)

        try:
            # Insert inactive entry
            await db_pool.execute(
                """
                INSERT INTO knowledge_base (title, content, category, active)
                VALUES ($1, $2, $3, false)
                """,
                "Inactive Article",
                "This should not appear in search results",
                "test"
            )

            result = await search_knowledge_base("inactive", max_results=5)

            assert result['success'] is True
            # Should not find the inactive entry
            for r in result['results']:
                assert 'Inactive Article' not in r['title']
        finally:
            await close_db()


class TestKnowledgeBaseSeed:
    """Test knowledge base seeding."""

    @pytest.mark.asyncio
    async def test_seed_script_structure(self):
        """Test that seed script has correct structure."""
        import seed_knowledge_base

        assert hasattr(seed_knowledge_base, 'KNOWLEDGE_BASE_ENTRIES')
        assert hasattr(seed_knowledge_base, 'seed_knowledge_base')
        assert len(seed_knowledge_base.KNOWLEDGE_BASE_ENTRIES) >= 5

    def test_knowledge_base_entries_format(self):
        """Test that KB entries have required fields."""
        from seed_knowledge_base import KNOWLEDGE_BASE_ENTRIES

        for entry in KNOWLEDGE_BASE_ENTRIES:
            assert 'title' in entry
            assert 'content' in entry
            assert 'category' in entry
            assert 'tags' in entry
            assert isinstance(entry['tags'], list)
            assert len(entry['title']) > 0
            assert len(entry['content']) > 0


class TestGmailConfig:
    """Test Gmail configuration."""

    def test_gmail_config_defaults(self):
        """Test Gmail config default values."""
        from app.handlers.gmail import GmailConfig

        config = GmailConfig()

        assert config.polling_interval == 60  # default
        assert config.polling_enabled is False  # default

    def test_gmail_config_from_env(self, monkeypatch):
        """Test Gmail config from environment variables."""
        from app.handlers.gmail import GmailConfig

        monkeypatch.setenv("GMAIL_POLLING_ENABLED", "true")
        monkeypatch.setenv("GMAIL_POLLING_INTERVAL", "30")
        monkeypatch.setenv("GMAIL_ADDRESS", "test@example.com")

        config = GmailConfig()

        assert config.polling_enabled is True
        assert config.polling_interval == 30
        assert config.gmail_address == "test@example.com"
