"""Test configuration for pytest (if used)."""

import shutil
import tempfile
from pathlib import Path

import pytest

from tests.test_helpers import TestEnvironmentHelper


@pytest.fixture(scope="session")
def test_environment():
    """Create a test environment for the entire test session."""
    env = TestEnvironmentHelper()
    env.setup()
    yield env
    env.teardown()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for each test."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_html_files(fixtures_dir):
    """Get paths to sample HTML files."""
    return {
        "module": fixtures_dir / "mock_module.html",
        "lesson": fixtures_dir / "mock_lesson.html",
        "trail": fixtures_dir / "mock_trail.html",
    }
