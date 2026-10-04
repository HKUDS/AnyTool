import pytest

from anytool.config.grounding import GroundingConfig
from anytool.grounding.core.grounding_client import GroundingClient
from anytool.grounding.core.types import BackendType


@pytest.mark.parametrize("enabled", [False, True])
def test_backend_enabled_flag_controls_provider_registration(enabled):
    config = GroundingConfig(enabled_backends=[{
        "name": "shell", "provider_cls": "anytool.grounding.backends.shell.provider.ShellProvider",
    }], shell={"enabled": enabled}, tool_quality={"enabled": False})
    client = GroundingClient(config)
    assert (BackendType.SHELL in client.list_providers()) == enabled
