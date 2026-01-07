"""
Fixtures for database unit tests.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_modules_and_env():
    """Reset module imports and environment before and after each test."""
    # Store original env vars
    original_url = os.environ.get("SUPABASE_URL")
    original_key = os.environ.get("SUPABASE_SERVICE_KEY")

    # Clear supabase_client from cache
    to_remove = [key for key in list(sys.modules.keys()) if "supabase_client" in key]
    for key in to_remove:
        del sys.modules[key]

    yield

    # Restore env vars
    if original_url:
        os.environ["SUPABASE_URL"] = original_url
    else:
        os.environ.pop("SUPABASE_URL", None)

    if original_key:
        os.environ["SUPABASE_SERVICE_KEY"] = original_key
    else:
        os.environ.pop("SUPABASE_SERVICE_KEY", None)

    # Clear again after test
    to_remove = [key for key in list(sys.modules.keys()) if "supabase_client" in key]
    for key in to_remove:
        del sys.modules[key]
