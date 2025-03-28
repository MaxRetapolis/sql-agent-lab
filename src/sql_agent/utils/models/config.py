"""
Configuration parameters for model management.
"""
from typing import Dict, Any, List
import os
from dataclasses import dataclass

# Default timeout values (in seconds)
DEFAULT_MODEL_TIMEOUTS = {
    # Model file operations (downloading, pulling)
    "model_download": 1200,  # 20 minutes for model downloads
    "model_file_operations": 600,  # 10 minutes for other file operations
    
    # Model connection and API operations
    "connection_check": 10,  # 10 seconds for basic connection checks
    "api_calls": 30,  # 30 seconds for API calls
    
    # Model inference operations
    "inference_first_token": 60,  # 60 seconds to get first token
    "inference_completion": 300,  # 5 minutes to complete generation
    
    # System operations
    "system_commands": 10,  # 10 seconds for system commands like 'which'
}

# Environment variable overrides for timeouts
def _get_timeout_from_env(key: str, default: int) -> int:
    """Get timeout value from environment or use default."""
    env_var = f"OLLAMA_TIMEOUT_{key.upper()}"
    if env_var in os.environ:
        try:
            return int(os.environ[env_var])
        except (ValueError, TypeError):
            pass
    return default

# Load timeouts from environment variables if available
MODEL_TIMEOUTS = {
    key: _get_timeout_from_env(key, value)
    for key, value in DEFAULT_MODEL_TIMEOUTS.items()
}

def get_timeout(operation_type: str) -> int:
    """Get timeout value for a specific operation type.
    
    Args:
        operation_type: The type of operation to get timeout for
        
    Returns:
        Timeout value in seconds
    """
    return MODEL_TIMEOUTS.get(operation_type, DEFAULT_MODEL_TIMEOUTS.get(operation_type, 60))


@dataclass
class RemoteModelConfig:
    """Configuration for a remote model provider."""
    name: str
    api_key_env: str  # Environment variable or secrets key for API key
    base_url: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60


# Default remote model configurations
DEFAULT_REMOTE_MODELS = {
    "haiku-3.5": RemoteModelConfig(
        name="Anthropic Haiku",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com/v1/messages",
        model_name="claude-3-haiku-20240307",
        max_tokens=4096,
        temperature=0.7,
        timeout=30
    ),
    # Add other remote models as needed
}