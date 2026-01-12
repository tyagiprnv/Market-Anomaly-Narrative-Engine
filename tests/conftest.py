"""Shared pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set minimal required environment variables for tests
    os.environ.setdefault("DATABASE__PASSWORD", "test_password")
    os.environ.setdefault("NEWS__CRYPTOPANIC_API_KEY", "test_key")
    os.environ.setdefault("NEWS__REDDIT_CLIENT_ID", "test_client_id")
    os.environ.setdefault("NEWS__REDDIT_CLIENT_SECRET", "test_secret")
    os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")

    yield

    # Cleanup is optional
