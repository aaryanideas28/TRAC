from pathlib import Path

import pytest

from railradar.config import DEFAULT_BASE_URL, load_settings
from railradar.exceptions import ConfigurationError


def test_configuration_loads_dotenv_and_environment_overrides(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAILRADAR_API_KEY=from-file\n"
        "RAILRADAR_TIMEOUT=8\n"
        "RAILRADAR_RETRY_COUNT=3\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file, {"RAILRADAR_API_KEY": "from-environment"})

    assert settings.api_key == "from-environment"
    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.timeout == 8
    assert settings.retry_count == 3


def test_missing_api_key_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="RAILRADAR_API_KEY"):
        load_settings(tmp_path / ".env", {})
