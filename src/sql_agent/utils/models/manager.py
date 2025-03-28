"""
Model manager module for handling Ollama model operations.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
from dataclasses import dataclass

from sql_agent.utils import logger
from sql_agent.utils.models.discovery import ModelInfo, OllamaDiscovery
from sql_agent.utils.models.config import get_timeout

log = logger.get_logger(__name__)

@dataclass
class ModelManagerConfig:
    """Configuration for the model manager."""
    ollama_host: Optional[str] = None
    default_model_id: str = "qwen2.5-coder:1.5b"
    model_blacklist: List[str] = None
    
    def __post_init__(self):
        if self.model_blacklist is None:
            # Models known to have tensor initialization issues
            self.model_blacklist = [
                "qwen2.5-coder:0.5b", 
                "llama3.2:1b"
            ]
        
        # Set default Ollama host if not provided
        if not self.ollama_host:
            self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class ModelManager:
    """Manages Ollama model operations including discovery, pulling, and status checks."""
    
    def __init__(self, config: Optional[ModelManagerConfig] = None):
        """Initialize the model manager.
        
        Args:
            config: Optional configuration for the model manager
        """
        self.config = config or ModelManagerConfig()
        self.ollama_host = self.config.ollama_host
        self.models = {}
        self.using_local_ollama = False
        self.ollama_mode = "remote"  # Can be "remote" or "local"
        self.current_model_id = self.config.default_model_id
        self.ollama_available = False
        
        # Initialize model discovery
        self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
        
        # Try to discover available models
        self.check_ollama_availability()
    
    def check_ollama_availability(self) -> bool:
        """Check if Ollama is available locally or remotely.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        # First try local Ollama
        try:
            import subprocess
            result = subprocess.run(
                ["which", "ollama"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=get_timeout("system_commands")
            )
            if result.returncode == 0:
                log.info("Local Ollama installation found")
                self.using_local_ollama = True
                self.ollama_mode = "local"
                # Use localhost for local Ollama
                self.ollama_host = "http://localhost:11434"
                self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
                # Try to discover local models
                try:
                    self.models = self.model_discovery.discover_models()
                    if self.models:
                        self.ollama_available = True
                        log.info(f"Found {len(self.models)} local models")
                    else:
                        log.warning("No local models found. Local Ollama might not be running.")
                        self.ollama_available = False
                except Exception as e:
                    log.warning(f"Failed to discover local Ollama models: {e}")
                    self.ollama_available = False
            else:
                log.info("No local Ollama installation found, using remote mode")
                self._try_remote_ollama()
        except Exception as e:
            log.warning(f"Error checking for local Ollama: {e}")
            self._try_remote_ollama()
            
        return self.ollama_available
    
    def _try_remote_ollama(self) -> bool:
        """Try to connect to remote Ollama server.
        
        Returns:
            True if successful, False otherwise
        """
        self.using_local_ollama = False
        self.ollama_mode = "remote"
        # Use the provided remote host
        self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
        try:
            self.models = self.model_discovery.discover_models()
            self.ollama_available = True
            log.info(f"Connected to remote Ollama at {self.ollama_host}")
            log.info(f"Found {len(self.models)} remote models")
            return True
        except Exception as e:
            log.warning(f"Failed to discover remote Ollama models: {e}")
            self.ollama_available = False
            return False
    
    def get_model_list(self) -> Dict[str, ModelInfo]:
        """Get the list of available models.
        
        Returns:
            Dict of model information
        """
        try:
            self.models = self.model_discovery.discover_models()
            self.ollama_available = True
        except Exception as e:
            log.warning(f"Failed to discover Ollama models: {e}")
            self.ollama_available = False
            
        return self.models
    
    def pull_model(self, model_id: str) -> bool:
        """Pull a model from Ollama server.
        
        Args:
            model_id: ID of the model to pull
            
        Returns:
            True if successful, False otherwise
        """
        if not self.using_local_ollama:
            log.warning("Cannot pull models in remote mode")
            return False
            
        try:
            import subprocess
            log.info(f"Pulling model {model_id}...")
            result = subprocess.run(
                ["ollama", "pull", model_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=get_timeout("model_download")
            )
            
            if result.returncode == 0:
                log.info(f"Successfully pulled model {model_id}")
                # Refresh model list
                self.models = self.model_discovery.discover_models()
                return True
            else:
                log.error(f"Failed to pull model {model_id}: {result.stderr}")
                return False
                
        except Exception as e:
            log.error(f"Error pulling model: {e}")
            return False
    
    def is_model_blacklisted(self, model_id: str) -> bool:
        """Check if a model is blacklisted.
        
        Args:
            model_id: ID of the model to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        return model_id in self.config.model_blacklist
    
    def test_model(self, model_id: str) -> Tuple[bool, Optional[str]]:
        """Test if a model works properly.
        
        Args:
            model_id: ID of the model to test
            
        Returns:
            Tuple of (success, error_message)
        """
        if self.is_model_blacklisted(model_id):
            return False, "Model is blacklisted due to known compatibility issues"
            
        try:
            # For local Ollama, run a quick CLI test
            if self.using_local_ollama:
                import subprocess
                test_prompt = "Generate 'Hello World'"
                cmd = ["ollama", "run", model_id, test_prompt, "--nowordwrap"]
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=get_timeout("inference_first_token")
                )
                
                if "tensor 'output.weight' not found" in result.stderr:
                    self.config.model_blacklist.append(model_id)
                    return False, "Tensor initialization error"
                    
                if result.returncode != 0:
                    return False, f"Model test failed: {result.stderr}"
                    
                return True, None
                
            # For remote Ollama, use API
            else:
                test_payload = {
                    "model": model_id,
                    "prompt": "Generate 'Hello World'",
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json=test_payload,
                    timeout=get_timeout("inference_first_token")
                )
                
                if response.status_code != 200:
                    return False, f"API error: {response.text}"
                    
                return True, None
                
        except subprocess.TimeoutExpired:
            return False, "Timeout waiting for model response"
            
        except Exception as e:
            return False, f"Error testing model: {str(e)}"
    
    def get_best_model(self) -> Tuple[str, bool]:
        """Get the best available model.
        
        Returns:
            Tuple of (model_id, is_fallback)
            - model_id: ID of the best model
            - is_fallback: True if a fallback model was selected
        """
        # If current model is available and not blacklisted, use it
        if (self.current_model_id in self.models and 
            not self.is_model_blacklisted(self.current_model_id)):
            return self.current_model_id, False
            
        # Models to try in order of preference
        fallback_models = [
            "qwen2.5-coder:1.5b",  # 986 MB
            "deepseek-r1:1.5b",    # 1.1 GB
            "phi:latest",          # 1.6 GB
            "gemma2:latest",       # 5.4 GB
            "qwen2.5-coder:0.5b",  # Smallest (531 MB) but has tensor issues
            "llama3.2:1b"          # 1.3 GB - has tensor issues
        ]
        
        # Go through fallback models
        for model_id in fallback_models:
            # Skip blacklisted models
            if self.is_model_blacklisted(model_id):
                log.info(f"Skipping blacklisted model: {model_id}")
                continue
                
            # If model is already available, use it
            if model_id in self.models:
                return model_id, True
                
            # For local Ollama, try to pull the model
            if self.using_local_ollama:
                if self.pull_model(model_id):
                    return model_id, True
        
        # If no model is available, return current model anyway
        return self.current_model_id, True
        
    def switch_to_local_mode(self) -> bool:
        """Switch to using local Ollama instance.
        
        Returns:
            True if successful, False otherwise
        """
        if self.using_local_ollama:
            log.info("Already in local mode")
            return True
        
        try:
            # Check if local Ollama is available
            import subprocess
            result = subprocess.run(
                ["which", "ollama"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=get_timeout("system_commands")
            )
            
            if result.returncode != 0:
                log.error("Local Ollama installation not found")
                return False
            
            # Save old settings
            old_mode = self.ollama_mode
            old_host = self.ollama_host
            old_model_id = self.current_model_id
            
            # Switch to local mode
            self.using_local_ollama = True
            self.ollama_mode = "local"
            self.ollama_host = "http://localhost:11434"
            
            # Create new model discovery
            self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
            
            # Try to discover local models
            try:
                self.models = self.model_discovery.discover_models()
                if not self.models:
                    log.warning("No local models found. Starting Ollama service...")
                    # Try to start local Ollama service
                    subprocess.Popen(
                        ["ollama", "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    # Wait a moment for Ollama to start
                    import time
                    time.sleep(2)
                    # Try again to discover models
                    self.models = self.model_discovery.discover_models()
            except Exception as e:
                log.error(f"Error discovering local models: {e}")
                self.models = {}
            
            # Check if the current model is available locally or needs to be pulled
            if old_model_id not in self.models:
                # Try to find a suitable local model
                if self.models:
                    # Use the first available model
                    self.current_model_id = next(iter(self.models.keys()))
                else:
                    # Try to pull a small model
                    try:
                        small_model = "qwen2.5-coder:1.5b"
                        log.info(f"Pulling {small_model}...")
                        result = subprocess.run(
                            ["ollama", "pull", small_model],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=get_timeout("model_download")
                        )
                        if result.returncode == 0:
                            self.current_model_id = small_model
                            # Refresh models
                            self.models = self.model_discovery.discover_models()
                        else:
                            log.error(f"Failed to pull model: {result.stderr}")
                            # Revert to previous mode
                            self.using_local_ollama = False
                            self.ollama_mode = old_mode
                            self.ollama_host = old_host
                            self.current_model_id = old_model_id
                            return False
                    except Exception as e:
                        log.error(f"Error pulling model: {e}")
                        # Revert to previous mode
                        self.using_local_ollama = False
                        self.ollama_mode = old_mode
                        self.ollama_host = old_host
                        self.current_model_id = old_model_id
                        return False
            
            log.info(f"Switched to local mode using model {self.current_model_id}")
            self.ollama_available = True
            return True
                
        except Exception as e:
            log.error(f"Error switching to local mode: {e}")
            return False
    
    def switch_to_remote_mode(self, host: Optional[str] = None) -> bool:
        """Switch to using remote Ollama instance.
        
        Args:
            host: Optional host address for Ollama
            
        Returns:
            True if successful, False otherwise
        """
        if not self.using_local_ollama and host is None:
            log.info("Already in remote mode")
            return True
        
        # Save old settings
        old_mode = self.ollama_mode
        old_using_local = self.using_local_ollama
        old_model_id = self.current_model_id
        old_host = self.ollama_host
        
        try:
            # Switch to remote mode
            self.using_local_ollama = False
            self.ollama_mode = "remote"
            # Use the provided host or previously configured remote host or default
            if host:
                self.ollama_host = host
            elif not self.ollama_host or self.ollama_host == "http://localhost:11434":
                self.ollama_host = "http://192.168.1.37:11434"  # Default remote host
            
            # Create new model discovery
            self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
            
            # Try to discover remote models
            try:
                self.models = self.model_discovery.discover_models()
                self.ollama_available = bool(self.models)
            except Exception as e:
                log.error(f"Error discovering remote models: {e}")
                self.models = {}
                self.ollama_available = False
            
            # Check if the current model is available remotely
            if not self.ollama_available or old_model_id not in self.models:
                if self.models:
                    # Use the first available model
                    self.current_model_id = next(iter(self.models.keys()))
                else:
                    # Use the default model
                    self.current_model_id = self.config.default_model_id
            else:
                # Keep using the same model
                self.current_model_id = old_model_id
            
            log.info(f"Switched to remote mode using model {self.current_model_id}")
            return self.ollama_available
                
        except Exception as e:
            log.error(f"Error switching to remote mode: {e}")
            # Revert to previous settings
            self.using_local_ollama = old_using_local
            self.ollama_mode = old_mode
            self.ollama_host = old_host
            self.current_model_id = old_model_id
            return False