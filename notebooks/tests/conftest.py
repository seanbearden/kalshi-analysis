"""Pytest configuration and fixtures for notebook testing."""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine

# Add notebooks directory to Python path for utils imports
NOTEBOOKS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(NOTEBOOKS_DIR))


@pytest.fixture(scope="session")
def notebooks_dir():
    """Return path to notebooks directory."""
    return NOTEBOOKS_DIR


@pytest.fixture(scope="session")
def test_db_url():
    """Return test database URL (or mock if not available)."""
    # Use environment variable or default to None (mocked)
    return os.getenv("TEST_DB_URL")


@pytest.fixture(scope="session")
def has_database(test_db_url):
    """Check if test database is available."""
    if not test_db_url:
        return False

    try:
        engine = create_engine(test_db_url)
        with engine.connect():
            return True
    except Exception:
        return False


@pytest.fixture
def mock_db_data():
    """Return mock data for testing without database."""
    import pandas as pd
    from datetime import datetime, timedelta

    # Generate sample market data
    base_time = datetime.now()
    data = []

    for i in range(100):
        data.append({
            'ticker': 'TEST-MARKET-1',
            'timestamp': base_time + timedelta(seconds=i*5),
            'yes_price': 45 + (i % 20),  # Oscillating price
            'no_price': 55 - (i % 20),
            'volume': 1000 + (i * 10),
            'source': 'test',
            'yes_prob': (45 + (i % 20)) / 100,
            'no_prob': (55 - (i % 20)) / 100
        })

    return pd.DataFrame(data)
