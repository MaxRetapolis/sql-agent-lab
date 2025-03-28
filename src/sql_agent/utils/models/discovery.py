"""Model discovery utilities."""
import os
import json
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from sql_agent.utils import logger
from sql_agent.utils.models.config import get_timeout

log = logger.get_logger(__name__)

@dataclass
class ModelInfo:
    """Information about a discovered model."""
    name: str
    size: str
    modified: str
    digest: str
    details: Optional[Dict[str, Any]] = None
    

class OllamaDiscovery:
    """Utility for discovering available Ollama models."""
    
    def __init__(self, ollama_host: Optional[str] = None):
        """Initialize the Ollama discovery utility.
        
        Args:
            ollama_host: Optional host address for Ollama (e.g., 'http://localhost:11434')
                         If None, will use OLLAMA_HOST environment variable or default to localhost
        """
        self.ollama_host = ollama_host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.models: Dict[str, ModelInfo] = {}
        
    def discover_models(self) -> Dict[str, ModelInfo]:
        """Discover all available Ollama models.
        
        Returns:
            Dict mapping model names to ModelInfo objects
        """
        log.info(f"Discovering models from Ollama host: {self.ollama_host}")
        self.models = {}
        
        try:
            # Try using the Ollama API directly
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=get_timeout("api_calls"))
            if response.status_code == 200:
                model_list = response.json().get("models", [])
                
                for model in model_list:
                    model_name = model.get("name")
                    self.models[model_name] = ModelInfo(
                        name=model_name,
                        size=self._format_size(model.get("size", 0)),
                        modified=model.get("modified", ""),
                        digest=model.get("digest", ""),
                    )
                    
                    # Try to get more details about the model
                    try:
                        details_response = requests.post(
                            f"{self.ollama_host}/api/show", 
                            json={"name": model_name},
                            timeout=get_timeout("api_calls")
                        )
                        if details_response.status_code == 200:
                            self.models[model_name].details = details_response.json()
                    except Exception as e:
                        log.warning(f"Error getting details for model {model_name}: {e}")
                
                log.info(f"Discovered {len(self.models)} models from Ollama API")
            else:
                log.warning(f"Error getting models from Ollama API: {response.status_code}")
                
        except requests.RequestException as e:
            log.warning(f"Could not connect to Ollama API at {self.ollama_host}: {e}")
            
            # Fallback to CLI if API doesn't work
            try:
                output = subprocess.check_output(["ollama", "list"], text=True)
                lines = output.strip().split("\n")
                
                # Skip header line
                if len(lines) > 1:
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 4:
                            model_name = parts[0]
                            size = parts[1] + " " + parts[2]
                            modified = " ".join(parts[3:])
                            
                            self.models[model_name] = ModelInfo(
                                name=model_name,
                                size=size,
                                modified=modified,
                                digest="",  # Not available from CLI output
                            )
                    
                    log.info(f"Discovered {len(self.models)} models from Ollama CLI")
            except Exception as e:
                log.error(f"Error discovering models using Ollama CLI: {e}")
        
        return self.models
    
    def get_model_details(self, model_name: str) -> Optional[ModelInfo]:
        """Get details about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo object if found, None otherwise
        """
        if model_name in self.models:
            return self.models[model_name]
        
        # If model not in cache, try to get it directly
        try:
            details_response = requests.post(
                f"{self.ollama_host}/api/show", 
                json={"name": model_name},
                timeout=get_timeout("api_calls")
            )
            if details_response.status_code == 200:
                details = details_response.json()
                return ModelInfo(
                    name=model_name,
                    size=self._format_size(details.get("size", 0)),
                    modified=details.get("modified", ""),
                    digest=details.get("digest", ""),
                    details=details
                )
        except Exception as e:
            log.warning(f"Error getting details for model {model_name}: {e}")
        
        return None
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama is available.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get(
                f"{self.ollama_host}/api/version", 
                timeout=get_timeout("connection_check")
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
            
    def get_ollama_info(self) -> Dict[str, Any]:
        """Get detailed information about the Ollama instance.
        
        Returns:
            Dictionary with Ollama version and status information
        """
        info = {
            "status": "unavailable",
            "host": self.ollama_host,
            "version": "unknown",
            "error": None
        }
        
        try:
            # Check version
            response = requests.get(f"{self.ollama_host}/api/version", timeout=get_timeout("connection_check"))
            if response.status_code == 200:
                info["status"] = "available"
                info["version"] = response.json().get("version", "unknown")
                
                # Try getting model list
                try:
                    models_response = requests.get(f"{self.ollama_host}/api/tags", timeout=get_timeout("api_calls"))
                    if models_response.status_code == 200:
                        model_count = len(models_response.json().get("models", []))
                        info["model_count"] = model_count
                except Exception as e:
                    info["error"] = f"Error getting models: {str(e)}"
            else:
                info["status"] = "error"
                info["error"] = f"HTTP status: {response.status_code}"
        except requests.RequestException as e:
            info["status"] = "connection_error"
            info["error"] = str(e)
            
        return info
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to a human-readable string.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g. '1.2 GB')
        """
        if not isinstance(size_bytes, (int, float)):
            return "Unknown"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024 or unit == 'TB':
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024