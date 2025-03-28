"""
Remote model provider integration module.
"""
import json
import requests
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import time

from sql_agent.utils import logger
from sql_agent.utils.models.config import RemoteModelConfig
from sql_agent.utils.models.secrets import secrets_manager

log = logger.get_logger(__name__)


class RemoteModelProvider:
    """Base class for remote model providers."""
    
    def __init__(self, config: RemoteModelConfig):
        """Initialize the remote model provider.
        
        Args:
            config: Configuration for the remote model
        """
        self.config = config
        self.api_key = secrets_manager.get_secret(config.api_key_env)
        
        if not self.api_key:
            log.warning(f"No API key found for {config.name}. "
                         f"Set the {config.api_key_env} environment variable or add it to secrets.")
    
    def is_available(self) -> bool:
        """Check if the remote model is available.
        
        Returns:
            True if available, False otherwise
        """
        return bool(self.api_key)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the remote API.
        
        Returns:
            Dict with connection status information
        """
        if not self.api_key:
            return {"status": "unavailable", "error": f"No API key found for {self.config.name}"}
        
        # Basic implementation - override in specific providers
        return {"status": "available"}
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text from prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text or None on error
        """
        raise NotImplementedError("Subclasses must implement the generate method")


class AnthropicProvider(RemoteModelProvider):
    """Anthropic Claude API provider."""
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the Anthropic API.
        
        Returns:
            Dict with connection status information
        """
        if not self.api_key:
            return {"status": "unavailable", "error": f"No API key found for {self.config.name}"}
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Just make a simple request to get model list
            response = requests.get(
                "https://api.anthropic.com/v1/models",
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "status": "available",
                    "models": [model.get("name") for model in models]
                }
            else:
                return {
                    "status": "error",
                    "error": f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text using Anthropic Claude API.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text or None on error
        """
        if not self.api_key:
            log.error(f"No API key found for {self.config.name}")
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # Get parameters from config with possible overrides from kwargs
            max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
            temperature = kwargs.get("temperature", self.config.temperature)
            
            # Prepare the request body
            data = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Send the request
            response = requests.post(
                self.config.base_url,
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("content", [{}])[0].get("text", "")
            else:
                log.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            log.error(f"Error generating text with {self.config.name}: {e}")
            return None


# Factory function to create providers based on name
def create_provider(config: RemoteModelConfig) -> RemoteModelProvider:
    """Create a remote model provider based on configuration.
    
    Args:
        config: Provider configuration
        
    Returns:
        Remote model provider instance
    """
    provider_name = config.name.lower()
    
    if "anthropic" in provider_name or "claude" in provider_name:
        return AnthropicProvider(config)
    
    # Add more providers as needed
    
    # Default to base class with warning
    log.warning(f"Unknown provider '{config.name}', using base implementation")
    return RemoteModelProvider(config)