"""Status reporter for SQL Agent."""
import os
import time
import threading
from typing import Dict, Any, Optional, Callable
from sql_agent.utils import logger
from sql_agent.utils.persistence import StatePersistence

log = logger.get_logger(__name__)

class StatusReporter:
    """Reporter for application status.
    
    Periodically dumps the application state to files:
    1. session_state.json - Machine-readable state for recovery
    2. SESSION_STATUS.md - Human-readable status summary
    """
    
    def __init__(
        self, 
        state_file: str = "app/data/session_state.json", 
        status_file: str = "SESSION_STATUS.md",
        auto_save_interval: int = 60,
        status_callback: Optional[Callable[[], Dict[str, Any]]] = None
    ):
        """Initialize the status reporter.
        
        Args:
            state_file: Path to the state file
            status_file: Path to the human-readable status file
            auto_save_interval: Interval in seconds for auto-saving state
            status_callback: Optional callback to get additional status information
        """
        self.status_file = status_file
        self.auto_save_interval = auto_save_interval
        self.status_callback = status_callback
        self.persistence = StatePersistence(state_file, auto_save_interval)
        self.running = False
        self.reporter_thread = None
    
    def start(self) -> None:
        """Start the status reporter thread."""
        if self.running:
            return
        
        self.running = True
        self.reporter_thread = threading.Thread(target=self._reporter_loop, daemon=True)
        self.reporter_thread.start()
        log.info(f"Started status reporter thread (interval: {self.auto_save_interval}s)")
    
    def stop(self) -> None:
        """Stop the status reporter thread."""
        self.running = False
        if self.reporter_thread and self.reporter_thread.is_alive():
            self.reporter_thread.join(timeout=3)
        log.info("Stopped status reporter thread")
    
    def _reporter_loop(self) -> None:
        """Main loop for the reporter thread."""
        while self.running:
            try:
                self._update_status_file()
                time.sleep(self.auto_save_interval)
            except Exception as e:
                log.error(f"Error in status reporter thread: {e}")
                time.sleep(10)  # Wait a bit longer if there was an error
    
    def _update_status_file(self) -> None:
        """Update the status file with current application state."""
        try:
            # Get additional status info if callback is provided
            additional_info = "\n\n## Additional Information\n"
            if self.status_callback:
                try:
                    status_info = self.status_callback()
                    for key, value in status_info.items():
                        additional_info += f"### {key}\n{value}\n\n"
                except Exception as e:
                    log.error(f"Error getting additional status info: {e}")
                    additional_info += f"Error getting additional status info: {e}\n"
            else:
                additional_info = ""
            
            # Generate status summary
            status_summary = self.persistence.dump_status_summary()
            
            # Add additional info
            if additional_info:
                status_summary += additional_info
            
            # Add recovery instructions
            status_summary += "\n## Recovery Instructions\n"
            status_summary += "If the application crashes or disconnects, use the following steps to recover:\n\n"
            status_summary += f"1. Check the state file at `{self.persistence.state_file}` for the latest state\n"
            status_summary += "2. Restart the application - it will automatically load the saved state\n"
            status_summary += "3. If automatic recovery fails, manually set the database and model using commands:\n"
            status_summary += f"   - `/db {self.persistence.state['current_db']}`\n"
            status_summary += f"   - `/model {self.persistence.state['current_model']}`\n"
            
            # Add timestamp
            status_summary += f"\n\nLast Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            # Write to status file
            with open(self.status_file, 'w') as f:
                f.write(status_summary)
            
            log.info(f"Updated status file: {self.status_file}")
        
        except Exception as e:
            log.error(f"Error updating status file: {e}")
    
    def update_now(self, force: bool = True) -> None:
        """Force an immediate update of the status file.
        
        Args:
            force: Force save even if auto-save interval hasn't elapsed
        """
        self.persistence.save_state(force=force)
        self._update_status_file()
        log.info("Forced status update")
    
    def update_database_info(self, databases: Dict[str, Any], current_db: str) -> None:
        """Update database information in the state.
        
        Args:
            databases: Dictionary of database information
            current_db: Current database name
        """
        self.persistence.update_database_info(databases, current_db)
        self._update_status_file()
    
    def update_model_info(self, models: Dict[str, Any], current_model: str) -> None:
        """Update model information in the state.
        
        Args:
            models: Dictionary of model information
            current_model: Current model name
        """
        self.persistence.update_model_info(models, current_model)
        self._update_status_file()
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration in the state.
        
        Args:
            config: Configuration dictionary
        """
        self.persistence.update_config(config)
        self._update_status_file()