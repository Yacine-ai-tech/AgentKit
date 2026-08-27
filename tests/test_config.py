"""
Test settings configuration in agentkit_mcp.core.config
"""

from agentkit_mcp.core.config import settings


def test_inference_settings_default():
    assert hasattr(settings, "INFERENCE_MODE")
    assert hasattr(settings, "LLM_ENDPOINT")
    assert hasattr(settings, "LLM_TOKEN")
    assert isinstance(settings.INFERENCE_MODE, str)
    assert isinstance(settings.LLM_ENDPOINT, str)
    assert isinstance(settings.LLM_TOKEN, str)
