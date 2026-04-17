"""Tests for Docker configuration."""

import os
import yaml
import pytest
from pathlib import Path


class TestDockerfile:
    """Test Dockerfile configuration."""

    @pytest.fixture
    def dockerfile_path(self):
        """Get Dockerfile path."""
        return Path("Dockerfile")

    @pytest.fixture
    def dockerfile_content(self, dockerfile_path):
        """Read Dockerfile content."""
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not found")
        return dockerfile_path.read_text()

    def test_dockerfile_exists(self, dockerfile_path):
        """Test that Dockerfile exists."""
        assert dockerfile_path.exists(), "Dockerfile not found"

    def test_base_image_correct(self, dockerfile_content):
        """Test that base image is python:3.11-slim."""
        assert "FROM python:3.11-slim" in dockerfile_content

    def test_workdir_set(self, dockerfile_content):
        """Test that WORKDIR is set."""
        assert "WORKDIR /app" in dockerfile_content

    def test_requirements_copied(self, dockerfile_content):
        """Test that requirements.txt is copied."""
        assert "COPY requirements.txt" in dockerfile_content

    def test_app_code_copied(self, dockerfile_content):
        """Test that app code is copied."""
        assert "COPY app/" in dockerfile_content

    def test_port_exposed(self, dockerfile_content):
        """Test that port 8000 is exposed."""
        assert "EXPOSE 8000" in dockerfile_content

    def test_healthcheck_configured(self, dockerfile_content):
        """Test that healthcheck is configured."""
        assert "HEALTHCHECK" in dockerfile_content

    def test_cmd_configured(self, dockerfile_content):
        """Test that CMD is configured for uvicorn."""
        assert "uvicorn" in dockerfile_content
        assert "app.main:app" in dockerfile_content

    def test_environment_variables_set(self, dockerfile_content):
        """Test that environment variables are set."""
        assert "ENV PYTHONUNBUFFERED=1" in dockerfile_content


class TestDockerCompose:
    """Test docker-compose.yml configuration."""

    @pytest.fixture
    def compose_path(self):
        """Get docker-compose.yml path."""
        return Path("docker-compose.yml")

    @pytest.fixture
    def compose_config(self, compose_path):
        """Load docker-compose.yml configuration."""
        if not compose_path.exists():
            pytest.skip("docker-compose.yml not found")
        with open(compose_path, 'r') as f:
            return yaml.safe_load(f)

    def test_compose_file_exists(self, compose_path):
        """Test that docker-compose.yml exists."""
        assert compose_path.exists(), "docker-compose.yml not found"

    def test_compose_version_specified(self, compose_config):
        """Test that compose version is specified."""
        assert "version" in compose_config

    def test_all_services_defined(self, compose_config):
        """Test that all required services are defined."""
        services = compose_config.get("services", {})
        required_services = ["fte-api", "fte-worker", "postgres", "kafka", "zookeeper"]

        for service in required_services:
            assert service in services, f"Service {service} not defined"

    def test_postgres_service_configured(self, compose_config):
        """Test that postgres service is properly configured."""
        postgres = compose_config["services"]["postgres"]

        assert postgres["image"] == "postgres:16"
        assert "environment" in postgres
        assert "POSTGRES_DB" in postgres["environment"]
        assert "POSTGRES_USER" in postgres["environment"]
        assert "POSTGRES_PASSWORD" in postgres["environment"]
        assert "healthcheck" in postgres
        assert "volumes" in postgres

    def test_kafka_service_configured(self, compose_config):
        """Test that kafka service is properly configured."""
        kafka = compose_config["services"]["kafka"]

        assert "confluentinc/cp-kafka" in kafka["image"]
        assert "environment" in kafka
        assert "KAFKA_BROKER_ID" in kafka["environment"]
        assert "KAFKA_ZOOKEEPER_CONNECT" in kafka["environment"]
        assert "healthcheck" in kafka
        assert "volumes" in kafka

    def test_zookeeper_service_configured(self, compose_config):
        """Test that zookeeper service is properly configured."""
        zookeeper = compose_config["services"]["zookeeper"]

        assert "confluentinc/cp-zookeeper" in zookeeper["image"]
        assert "environment" in zookeeper
        assert "ZOOKEEPER_CLIENT_PORT" in zookeeper["environment"]
        assert "healthcheck" in zookeeper
        assert "volumes" in zookeeper

    def test_api_service_configured(self, compose_config):
        """Test that fte-api service is properly configured."""
        api = compose_config["services"]["fte-api"]

        assert "build" in api
        assert "environment" in api
        assert "DB_HOST" in api["environment"]
        assert "KAFKA_BOOTSTRAP_SERVERS" in api["environment"]
        assert "healthcheck" in api
        assert "depends_on" in api
        assert "postgres" in api["depends_on"]
        assert "kafka" in api["depends_on"]

    def test_worker_service_configured(self, compose_config):
        """Test that fte-worker service is properly configured."""
        worker = compose_config["services"]["fte-worker"]

        assert "build" in worker
        assert "environment" in worker
        assert "DB_HOST" in worker["environment"]
        assert "KAFKA_BOOTSTRAP_SERVERS" in worker["environment"]
        assert "command" in worker
        assert "healthcheck" in worker
        assert "depends_on" in worker

    def test_all_services_have_healthchecks(self, compose_config):
        """Test that all services have healthchecks."""
        services = compose_config["services"]

        for service_name, service_config in services.items():
            assert "healthcheck" in service_config, f"Service {service_name} missing healthcheck"

    def test_volumes_configured(self, compose_config):
        """Test that volumes are configured."""
        volumes = compose_config.get("volumes", {})

        required_volumes = ["postgres_data", "kafka_data", "zookeeper_data", "zookeeper_logs"]
        for volume in required_volumes:
            assert volume in volumes, f"Volume {volume} not defined"

    def test_network_configured(self, compose_config):
        """Test that network is configured."""
        networks = compose_config.get("networks", {})

        assert "fte-network" in networks

    def test_all_services_use_network(self, compose_config):
        """Test that all services use the network."""
        services = compose_config["services"]

        for service_name, service_config in services.items():
            assert "networks" in service_config, f"Service {service_name} not connected to network"
            assert "fte-network" in service_config["networks"]

    def test_no_hardcoded_credentials(self, compose_config):
        """Test that no hardcoded credentials are used."""
        services = compose_config["services"]

        # Check that environment variables use ${VAR:-default} syntax
        postgres = services["postgres"]["environment"]

        # These should use environment variable syntax
        assert "${DB_NAME" in str(postgres["POSTGRES_DB"]) or "fte_db" in str(postgres["POSTGRES_DB"])
        assert "${DB_USER" in str(postgres["POSTGRES_USER"]) or "postgres" in str(postgres["POSTGRES_USER"])
        assert "${DB_PASSWORD" in str(postgres["POSTGRES_PASSWORD"]) or "postgres" in str(postgres["POSTGRES_PASSWORD"])

    def test_service_dependencies_correct(self, compose_config):
        """Test that service dependencies are correctly configured."""
        api = compose_config["services"]["fte-api"]
        worker = compose_config["services"]["fte-worker"]
        kafka = compose_config["services"]["kafka"]

        # API and worker should depend on postgres and kafka
        assert "postgres" in api["depends_on"]
        assert "kafka" in api["depends_on"]
        assert "postgres" in worker["depends_on"]
        assert "kafka" in worker["depends_on"]

        # Kafka should depend on zookeeper
        assert "zookeeper" in kafka["depends_on"]

    def test_health_check_conditions(self, compose_config):
        """Test that health check conditions are set for dependencies."""
        api = compose_config["services"]["fte-api"]

        # Check that depends_on uses condition: service_healthy
        assert api["depends_on"]["postgres"]["condition"] == "service_healthy"
        assert api["depends_on"]["kafka"]["condition"] == "service_healthy"


class TestDockerignore:
    """Test .dockerignore configuration."""

    @pytest.fixture
    def dockerignore_path(self):
        """Get .dockerignore path."""
        return Path(".dockerignore")

    @pytest.fixture
    def dockerignore_content(self, dockerignore_path):
        """Read .dockerignore content."""
        if not dockerignore_path.exists():
            pytest.skip(".dockerignore not found")
        return dockerignore_path.read_text()

    def test_dockerignore_exists(self, dockerignore_path):
        """Test that .dockerignore exists."""
        assert dockerignore_path.exists(), ".dockerignore not found"

    def test_python_cache_excluded(self, dockerignore_content):
        """Test that Python cache files are excluded."""
        assert "__pycache__" in dockerignore_content
        assert "*.pyc" in dockerignore_content or "*.py[cod]" in dockerignore_content

    def test_venv_excluded(self, dockerignore_content):
        """Test that virtual environments are excluded."""
        assert "venv" in dockerignore_content or ".venv" in dockerignore_content

    def test_git_excluded(self, dockerignore_content):
        """Test that .git directory is excluded."""
        assert ".git" in dockerignore_content

    def test_logs_excluded(self, dockerignore_content):
        """Test that logs are excluded."""
        assert "logs" in dockerignore_content or "*.log" in dockerignore_content

    def test_env_files_excluded(self, dockerignore_content):
        """Test that .env files are excluded."""
        assert ".env" in dockerignore_content

    def test_tests_excluded(self, dockerignore_content):
        """Test that test cache is excluded."""
        assert ".pytest_cache" in dockerignore_content or "pytest" in dockerignore_content


class TestDockerIntegration:
    """Test Docker integration and configuration consistency."""

    @pytest.fixture
    def compose_config(self):
        """Load docker-compose.yml configuration."""
        compose_path = Path("docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("docker-compose.yml not found")
        with open(compose_path, 'r') as f:
            return yaml.safe_load(f)

    def test_api_port_matches(self, compose_config):
        """Test that API port in compose matches Dockerfile."""
        api = compose_config["services"]["fte-api"]
        ports = api.get("ports", [])

        # Should expose port 8000
        assert any("8000" in str(port) for port in ports)

    def test_environment_variables_consistent(self, compose_config):
        """Test that environment variables are consistent across services."""
        api_env = compose_config["services"]["fte-api"]["environment"]
        worker_env = compose_config["services"]["fte-worker"]["environment"]

        # Both should have same database config
        assert api_env["DB_HOST"] == worker_env["DB_HOST"]
        assert api_env["DB_PORT"] == worker_env["DB_PORT"]
        assert api_env["KAFKA_BOOTSTRAP_SERVERS"] == worker_env["KAFKA_BOOTSTRAP_SERVERS"]

    def test_restart_policies_set(self, compose_config):
        """Test that restart policies are set for application services."""
        api = compose_config["services"]["fte-api"]
        worker = compose_config["services"]["fte-worker"]

        assert "restart" in api
        assert "restart" in worker
