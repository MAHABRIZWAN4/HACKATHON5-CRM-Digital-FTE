"""Tests for FastAPI application."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.db.config import DatabaseConfig
from app.db.connection import init_db, close_db


@pytest_asyncio.fixture
async def app():
    """Create test FastAPI application."""
    # Initialize database for testing
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

    # Create app without lifespan (we manage DB manually)
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.core.config import get_settings
    from app.middleware.error_handler import ErrorHandlerMiddleware
    from app.api.routers import health, webhooks, support

    settings = get_settings()
    test_app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.add_middleware(ErrorHandlerMiddleware)

    test_app.include_router(health.router)
    test_app.include_router(webhooks.router)
    test_app.include_router(support.router)

    yield test_app

    # Cleanup
    await close_db()


@pytest_asyncio.fixture
async def client(app):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check returns 200 when database is connected."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_database_connection(self, client):
        """Test health check verifies database connectivity."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert data["database"] == "connected"


class TestWebhookEndpoints:
    """Test webhook endpoints."""

    @pytest.mark.asyncio
    async def test_gmail_webhook_success(self, client):
        """Test Gmail webhook accepts POST requests."""
        payload = {
            "message": "test email",
            "from": "test@example.com",
            "subject": "Test Subject"
        }

        response = await client.post("/webhooks/gmail", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["channel"] == "gmail"
        assert "ticket_id" in data

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_success(self, client):
        """Test WhatsApp webhook accepts POST requests."""
        payload = {
            "MessageSid": "SM123",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "Body": "test message",
            "NumMedia": "0"
        }

        response = await client.post("/webhooks/whatsapp", data=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["channel"] == "whatsapp"
        assert "ticket_id" in data

    @pytest.mark.asyncio
    async def test_gmail_webhook_empty_body(self, client):
        """Test Gmail webhook handles empty body."""
        response = await client.post("/webhooks/gmail", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_whatsapp_webhook_empty_body(self, client):
        """Test WhatsApp webhook handles empty body."""
        response = await client.post("/webhooks/whatsapp", data={"NumMedia": "0"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestSupportEndpoint:
    """Test support form endpoint."""

    @pytest.mark.asyncio
    async def test_support_request_success(self, client):
        """Test support form submission succeeds with valid data."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Need help with account",
            "message": "I cannot access my account. Please help."
        }

        response = await client.post("/support", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["channel"] == "web_form"
        assert "ticket_id" in data

    @pytest.mark.asyncio
    async def test_support_request_invalid_email(self, client):
        """Test support form rejects invalid email."""
        payload = {
            "name": "John Doe",
            "email": "invalid-email",
            "subject": "Test",
            "message": "Test message"
        }

        response = await client.post("/support", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_support_request_missing_fields(self, client):
        """Test support form rejects missing required fields."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com"
            # Missing subject and message
        }

        response = await client.post("/support", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_support_request_empty_name(self, client):
        """Test support form rejects empty name."""
        payload = {
            "name": "",
            "email": "john@example.com",
            "subject": "Test",
            "message": "Test message"
        }

        response = await client.post("/support", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_support_request_long_message(self, client):
        """Test support form accepts long messages within limit."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Long message test",
            "message": "A" * 4999  # Just under 5000 char limit
        }

        response = await client.post("/support", json=payload)

        assert response.status_code == 201


class TestCORSMiddleware:
    """Test CORS middleware."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origins(self, client):
        """Test CORS allows configured origins."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling middleware."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoints."""
        response = await client.get("/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method."""
        response = await client.get("/webhooks/gmail")  # Should be POST

        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_invalid_json_body(self, client):
        """Test error handling for invalid JSON."""
        response = await client.post(
            "/webhooks/gmail",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]


class TestDatabaseIntegration:
    """Test database integration."""

    @pytest.mark.asyncio
    async def test_health_check_uses_database(self, client):
        """Test health check actually queries database."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"

    @pytest.mark.asyncio
    async def test_endpoints_work_with_database_connected(self, client):
        """Test all endpoints work when database is connected."""
        # Health check
        response = await client.get("/health")
        assert response.status_code == 200

        # Gmail webhook
        response = await client.post("/webhooks/gmail", json={"test": "data"})
        assert response.status_code == 200

        # WhatsApp webhook
        response = await client.post("/webhooks/whatsapp", data={"NumMedia": "0"})
        assert response.status_code == 200

        # Support form
        response = await client.post("/support", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test",
            "message": "Test message"
        })
        assert response.status_code == 201
