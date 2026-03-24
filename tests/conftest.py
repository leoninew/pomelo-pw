"""Test configuration."""

from typing import Any

import pytest


@pytest.fixture
def sample_flow() -> dict[str, Any]:
    """Sample flow for testing."""
    return {
        "name": "test-flow",
        "variables": {
            "base_url": "https://example.com",
            "username": "admin",
        },
        "steps": [
            {"type": "navigate", "url": "${base_url}/login"},
            {"type": "screenshot", "file": "login.png"},
        ],
    }
