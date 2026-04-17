"""Tests for async database connection layer."""

import pytest
import pytest_asyncio
import asyncio
from app.db.config import DatabaseConfig
from app.db.connection import DatabasePool, init_db, close_db, get_db_pool


@pytest.fixture
def db_config():
    """Create test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="fte_db",
        pool_min_size=2,
        pool_max_size=5,
        pool_timeout=10.0,
    )


@pytest_asyncio.fixture
async def db_pool(db_config):
    """Create and cleanup database pool for tests."""
    pool = DatabasePool(db_config)
    await pool.connect()
    yield pool
    await pool.disconnect()


class TestDatabaseConfig:
    """Test DatabaseConfig class."""

    def test_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("DB_HOST", "testhost")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.setenv("DB_NAME", "testdb")
        monkeypatch.setenv("DB_POOL_MIN_SIZE", "5")
        monkeypatch.setenv("DB_POOL_MAX_SIZE", "15")
        monkeypatch.setenv("DB_POOL_TIMEOUT", "20.0")

        config = DatabaseConfig.from_env()

        assert config.host == "testhost"
        assert config.port == 5433
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.database == "testdb"
        assert config.pool_min_size == 5
        assert config.pool_max_size == 15
        assert config.pool_timeout == 20.0

    def test_get_dsn(self, db_config):
        """Test DSN generation."""
        dsn = db_config.get_dsn()
        assert dsn == "postgresql://postgres:postgres@localhost:5432/fte_db"

    def test_validate_success(self, db_config):
        """Test successful validation."""
        db_config.validate()  # Should not raise

    def test_validate_missing_host(self, db_config):
        """Test validation fails with missing host."""
        db_config.host = ""
        with pytest.raises(ValueError, match="DB_HOST is required"):
            db_config.validate()

    def test_validate_missing_user(self, db_config):
        """Test validation fails with missing user."""
        db_config.user = ""
        with pytest.raises(ValueError, match="DB_USER is required"):
            db_config.validate()

    def test_validate_invalid_pool_min_size(self, db_config):
        """Test validation fails with invalid pool_min_size."""
        db_config.pool_min_size = 0
        with pytest.raises(ValueError, match="DB_POOL_MIN_SIZE must be at least 1"):
            db_config.validate()

    def test_validate_invalid_pool_max_size(self, db_config):
        """Test validation fails when max < min."""
        db_config.pool_min_size = 10
        db_config.pool_max_size = 5
        with pytest.raises(ValueError, match="DB_POOL_MAX_SIZE must be >= DB_POOL_MIN_SIZE"):
            db_config.validate()


class TestDatabasePool:
    """Test DatabasePool class."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, db_config):
        """Test pool connection and disconnection."""
        pool = DatabasePool(db_config)

        # Connect
        await pool.connect()
        assert pool._pool is not None

        # Disconnect
        await pool.disconnect()
        assert pool._pool is None

    @pytest.mark.asyncio
    async def test_connect_twice_warning(self, db_config, caplog):
        """Test connecting twice logs warning."""
        pool = DatabasePool(db_config)
        await pool.connect()
        await pool.connect()  # Second connect should warn

        assert "Database pool already initialized" in caplog.text

        await pool.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_without_connect(self, db_config, caplog):
        """Test disconnecting without connecting logs warning."""
        pool = DatabasePool(db_config)
        await pool.disconnect()

        assert "Database pool not initialized" in caplog.text

    @pytest.mark.asyncio
    async def test_execute_query(self, db_pool):
        """Test executing a query."""
        result = await db_pool.execute("SELECT 1")
        assert result == "SELECT 1"

    @pytest.mark.asyncio
    async def test_fetch_query(self, db_pool):
        """Test fetching multiple rows."""
        rows = await db_pool.fetch("SELECT 1 as num UNION SELECT 2")
        assert len(rows) == 2
        assert rows[0]["num"] == 1
        assert rows[1]["num"] == 2

    @pytest.mark.asyncio
    async def test_fetchrow_query(self, db_pool):
        """Test fetching a single row."""
        row = await db_pool.fetchrow("SELECT 1 as num, 'test' as text")
        assert row["num"] == 1
        assert row["text"] == "test"

    @pytest.mark.asyncio
    async def test_fetchval_query(self, db_pool):
        """Test fetching a single value."""
        value = await db_pool.fetchval("SELECT 42")
        assert value == 42

    @pytest.mark.asyncio
    async def test_acquire_connection(self, db_pool):
        """Test acquiring a connection from pool."""
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_acquire_without_connect(self, db_config):
        """Test acquiring connection without connecting raises error."""
        pool = DatabasePool(db_config)

        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            async with pool.acquire() as conn:
                pass

    @pytest.mark.asyncio
    async def test_pool_property(self, db_pool):
        """Test accessing pool property."""
        pool = db_pool.pool
        assert pool is not None

    @pytest.mark.asyncio
    async def test_pool_property_without_connect(self, db_config):
        """Test accessing pool property without connecting raises error."""
        pool = DatabasePool(db_config)

        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            _ = pool.pool

    @pytest.mark.asyncio
    async def test_database_operations(self, db_pool):
        """Test real database operations."""
        # Create a test table
        await db_pool.execute("""
            CREATE TEMP TABLE test_table (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        # Insert data
        await db_pool.execute(
            "INSERT INTO test_table (name) VALUES ($1), ($2)",
            "Alice", "Bob"
        )

        # Fetch data
        rows = await db_pool.fetch("SELECT * FROM test_table ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["name"] == "Bob"

        # Fetch single row
        row = await db_pool.fetchrow("SELECT * FROM test_table WHERE name = $1", "Alice")
        assert row["name"] == "Alice"

        # Fetch single value
        count = await db_pool.fetchval("SELECT COUNT(*) FROM test_table")
        assert count == 2


class TestGlobalPool:
    """Test global pool management functions."""

    @pytest.mark.asyncio
    async def test_init_and_close_db(self, db_config):
        """Test initializing and closing global pool."""
        # Initialize
        pool = await init_db(db_config)
        assert pool is not None

        # Get pool
        retrieved_pool = get_db_pool()
        assert retrieved_pool is pool

        # Close
        await close_db()

        # Should raise after closing
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            get_db_pool()

    @pytest.mark.asyncio
    async def test_get_db_pool_without_init(self):
        """Test getting pool without initialization raises error."""
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            get_db_pool()

    @pytest.mark.asyncio
    async def test_init_db_twice(self, db_config, caplog):
        """Test initializing database twice logs warning."""
        await init_db(db_config)
        await init_db(db_config)  # Second init should warn

        assert "Database pool already initialized" in caplog.text

        await close_db()

    @pytest.mark.asyncio
    async def test_close_db_without_init(self, caplog):
        """Test closing database without initialization logs warning."""
        await close_db()

        assert "Database pool not initialized" in caplog.text
