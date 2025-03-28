"""
Secrets management for remote model access.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Any

# Default secrets file location - in user's home directory
DEFAULT_SECRETS_FILE = Path.home() / ".sql_agent_secrets"

class SecretsManager:
    """Manager for storing and retrieving API keys and other secrets."""
    
    def __init__(self, secrets_file: Optional[str] = None):
        """Initialize the secrets manager.
        
        Args:
            secrets_file: Optional path to the secrets file
        """
        self.secrets_file = Path(secrets_file) if secrets_file else DEFAULT_SECRETS_FILE
        self.secrets = {}
        self._load_secrets()
    
    def _load_secrets(self) -> None:
        """Load secrets from file."""
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            self.secrets[key.strip()] = value.strip()
            except Exception as e:
                print(f"Error loading secrets: {e}")
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """Get a secret by key.
        
        Args:
            key: The secret key
            default: Default value if key not found
            
        Returns:
            The secret value or default
        """
        # Try getting from environment first (higher priority)
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value
            
        # Try getting from secrets file
        return self.secrets.get(key, default)
    
    def set_secret(self, key: str, value: str, save: bool = True) -> None:
        """Set a secret value.
        
        Args:
            key: The secret key
            value: The secret value
            save: Whether to save the secret to file
        """
        self.secrets[key] = value
        if save:
            self._save_secrets()
    
    def _save_secrets(self) -> None:
        """Save secrets to file."""
        try:
            # Make sure directory exists
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write secrets to file
            with open(self.secrets_file, "w") as f:
                for key, value in self.secrets.items():
                    f.write(f"{key}={value}\n")
                
            # Set proper permissions (read/write only for owner)
            os.chmod(self.secrets_file, 0o600)
        except Exception as e:
            print(f"Error saving secrets: {e}")

# Create singleton instance
secrets_manager = SecretsManager()