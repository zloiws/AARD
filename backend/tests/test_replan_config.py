"""
Tests for automatic replanning configuration
"""
import os
from unittest.mock import patch

import pytest
from app.core.config import Settings, get_settings


def test_replanning_config_defaults():
    """Test default values for replanning configuration"""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "OLLAMA_URL_1": "http://localhost:11434/v1",
        "OLLAMA_MODEL_1": "test-model",
        "OLLAMA_URL_2": "http://localhost:11434/v1",
        "OLLAMA_MODEL_2": "test-model"
    }):
        # Clear cache to reload settings
        get_settings.cache_clear()
        settings = get_settings()
        
        # Check defaults
        assert settings.enable_auto_replanning is True
        assert settings.auto_replanning_max_attempts == 3
        assert settings.auto_replanning_min_interval_seconds == 5
        assert settings.auto_replanning_timeout_seconds == 300
        assert settings.auto_replanning_trigger_critical is True
        assert settings.auto_replanning_trigger_high is True
        assert settings.auto_replanning_trigger_medium is False
        assert settings.auto_replanning_require_human_intervention_after == 5


def test_replanning_config_custom_values():
    """Test custom values for replanning configuration"""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "OLLAMA_URL_1": "http://localhost:11434/v1",
        "OLLAMA_MODEL_1": "test-model",
        "OLLAMA_URL_2": "http://localhost:11434/v1",
        "OLLAMA_MODEL_2": "test-model",
        "ENABLE_AUTO_REPLANNING": "false",
        "AUTO_REPLANNING_MAX_ATTEMPTS": "5",
        "AUTO_REPLANNING_MIN_INTERVAL_SECONDS": "10",
        "AUTO_REPLANNING_TIMEOUT_SECONDS": "600",
        "AUTO_REPLANNING_TRIGGER_CRITICAL": "true",
        "AUTO_REPLANNING_TRIGGER_HIGH": "false",
        "AUTO_REPLANNING_TRIGGER_MEDIUM": "true",
        "AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER": "3"
    }):
        # Clear cache to reload settings
        get_settings.cache_clear()
        settings = get_settings()
        
        # Check custom values
        assert settings.enable_auto_replanning is False
        assert settings.auto_replanning_max_attempts == 5
        assert settings.auto_replanning_min_interval_seconds == 10
        assert settings.auto_replanning_timeout_seconds == 600
        assert settings.auto_replanning_trigger_critical is True
        assert settings.auto_replanning_trigger_high is False
        assert settings.auto_replanning_trigger_medium is True
        assert settings.auto_replanning_require_human_intervention_after == 3


def test_replanning_config_validation():
    """Test validation of replanning configuration values"""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "OLLAMA_URL_1": "http://localhost:11434/v1",
        "OLLAMA_MODEL_1": "test-model",
        "OLLAMA_URL_2": "http://localhost:11434/v1",
        "OLLAMA_MODEL_2": "test-model",
        "AUTO_REPLANNING_MAX_ATTEMPTS": "0"  # Invalid: should be >= 1
    }):
        # Clear cache
        get_settings.cache_clear()
        
        # Should raise validation error
        with pytest.raises(Exception):
            settings = get_settings()


def test_replanning_config_bounds():
    """Test bounds validation for numeric config values"""
    with patch.dict(os.environ, {
        "SECRET_KEY": "test-secret",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "OLLAMA_URL_1": "http://localhost:11434/v1",
        "OLLAMA_MODEL_1": "test-model",
        "OLLAMA_URL_2": "http://localhost:11434/v1",
        "OLLAMA_MODEL_2": "test-model",
        "AUTO_REPLANNING_MAX_ATTEMPTS": "15"  # Invalid: should be <= 10
    }):
        # Clear cache
        get_settings.cache_clear()
        
        # Should raise validation error
        with pytest.raises(Exception):
            settings = get_settings()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

