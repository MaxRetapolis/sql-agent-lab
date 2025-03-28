"""State persistence utilities for SQL Agent."""
import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from sql_agent.utils import logger

log = logger.get_logger(__name__)

class StatePersistence:
    """Utility for persisting and restoring application state."""
    
    def __init__(self, state_file: str = "app/data/session_state.json", auto_save_interval: int = 60):
        """Initialize the state persistence utility.
        
        Args:
            state_file: Path to the state file
            auto_save_interval: Interval in seconds for auto-saving state (0 to disable)
        """
        self.state_file = state_file
        self.auto_save_interval = auto_save_interval
        self.last_save_time = 0
        self.state: Dict[str, Any] = {
            "version": 1,
            "last_updated": time.time(),
            "databases": {},
            "current_db": None,
            "models": {},
            "current_model": None,
            "config": {
                "ollama_host": "http://localhost:11434",
                "ui_port": 8046
            }
        }
        
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        # Try to load existing state
        self.load_state()
    
    def save_state(self, force: bool = False) -> bool:
        """Save the current state to the state file.
        
        Args:
            force: Force save even if auto-save interval hasn't elapsed
            
        Returns:
            True if state was saved, False otherwise
        """
        current_time = time.time()
        
        # Check if we should auto-save
        if not force and self.auto_save_interval > 0:
            if current_time - self.last_save_time < self.auto_save_interval:
                return False
        
        try:
            # Update timestamp
            self.state["last_updated"] = current_time
            
            # Write state to file
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            self.last_save_time = current_time
            log.info(f"Saved state to {self.state_file}")
            return True
        
        except Exception as e:
            log.error(f"Error saving state: {e}")
            return False
    
    def load_state(self) -> Dict[str, Any]:
        """Load state from the state file.
        
        Returns:
            The loaded state dict
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    loaded_state = json.load(f)
                
                # Update our state with loaded values
                self.state.update(loaded_state)
                log.info(f"Loaded state from {self.state_file}")
        
        except Exception as e:
            log.error(f"Error loading state: {e}")
        
        return self.state
    
    def update_database_info(self, databases: Dict[str, Any], current_db: str) -> None:
        """Update database information in the state.
        
        Args:
            databases: Dictionary of database information
            current_db: Current database name
        """
        # Convert complex objects to serializable form
        serializable_dbs = {}
        for name, db_info in databases.items():
            if hasattr(db_info, '__dict__'):
                serializable_dbs[name] = {
                    "name": name,
                    "path": getattr(db_info, 'path', ''),
                    "url": getattr(db_info, 'url', ''),
                    "tables": getattr(db_info, 'tables', [])
                }
            else:
                serializable_dbs[name] = db_info
        
        self.state["databases"] = serializable_dbs
        self.state["current_db"] = current_db
        
        # Auto-save if enabled
        self.save_state()
    
    def update_model_info(self, models: Dict[str, Any], current_model: str) -> None:
        """Update model information in the state.
        
        Args:
            models: Dictionary of model information
            current_model: Current model name
        """
        # Convert complex objects to serializable form
        serializable_models = {}
        for name, model_info in models.items():
            if hasattr(model_info, '__dict__'):
                serializable_models[name] = {
                    "name": name,
                    "size": getattr(model_info, 'size', ''),
                    "modified": getattr(model_info, 'modified', ''),
                    "digest": getattr(model_info, 'digest', '')
                }
            else:
                serializable_models[name] = model_info
        
        self.state["models"] = serializable_models
        self.state["current_model"] = current_model
        
        # Auto-save if enabled
        self.save_state()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration in the state.
        
        Args:
            config: Configuration dictionary
        """
        self.state["config"].update(config)
        
        # Auto-save if enabled
        self.save_state()
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information from the state.
        
        Returns:
            Dictionary with database info and current database
        """
        return {
            "databases": self.state["databases"],
            "current_db": self.state["current_db"]
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information from the state.
        
        Returns:
            Dictionary with model info and current model
        """
        return {
            "models": self.state["models"],
            "current_model": self.state["current_model"]
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration from the state.
        
        Returns:
            Configuration dictionary
        """
        return self.state["config"]
    
    def dump_status_summary(self) -> str:
        """Create a human-readable summary of the state.
        
        Returns:
            Summary string
        """
        summary = [
            "# SQL Agent Session State",
            f"Last Updated: {time.ctime(self.state['last_updated'])}",
            "",
            "## Configuration",
            f"- Ollama Host: {self.state['config'].get('ollama_host', 'Unknown')}",
            f"- UI Port: {self.state['config'].get('ui_port', 'Unknown')}",
            "",
            "## Database Information",
            f"- Current Database: {self.state['current_db']}",
            "- Available Databases:"
        ]
        
        for db_name in self.state["databases"]:
            summary.append(f"  - {db_name}")
        
        summary.extend([
            "",
            "## Model Information",
            f"- Current Model: {self.state['current_model']}",
            "- Available Models:"
        ])
        
        for model_name in self.state["models"]:
            model_size = ""
            if isinstance(self.state["models"][model_name], dict):
                model_size = self.state["models"][model_name].get("size", "")
            if model_size:
                summary.append(f"  - {model_name} ({model_size})")
            else:
                summary.append(f"  - {model_name}")
        
        return "\n".join(summary)