import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Annotated, Literal, Any, Optional, List, Dict, Tuple
from dataclasses import dataclass
from agno.models.ollama import Ollama
from ollama import Client as OllamaClient
from agno.tools.sql import SQLTools
from sqlalchemy import create_engine, inspect
from agno.agent import Agent
from sql_agent.prompt import TEXT2SQL_TEMPLATE, FULL_REPORT, DATABASE_SELECT_TEMPLATE, MODEL_SELECT_TEMPLATE
from sql_agent.utils import logger
from sql_agent.utils.database.discovery import DatabaseDiscovery, DatabaseInfo
from sql_agent.utils.models.discovery import OllamaDiscovery, ModelInfo
import pandas as pd

log = logger.get_logger(__name__)


@dataclass
class Text2SQLAgent:
    """ Text to SQL Agent to convert natural language to SQL """
    db_url: Optional[str] = None
    data_dir: str = "app/data"
    model_id: str = "qwen2.5-coder:7b"
    ollama_host: Optional[str] = None
    
    def __post_init__(self):
        # Initialize database discovery
        self.db_discovery = DatabaseDiscovery(self.data_dir)
        self.databases = self.db_discovery.discover_databases()
        
        # Initialize model discovery with default settings
        self.using_local_ollama = False
        self.ollama_mode = "remote"  # Can be "remote" or "local"
        self.models = {}
        
        # Try to discover models, but continue even if Ollama isn't available
        self.check_ollama_availability()
        
        # Set the default database if db_url is not provided
        if not self.db_url and self.databases:
            # Use the first available database by default
            first_db = next(iter(self.databases.values()))
            self.db_url = first_db.url
            self.current_db_name = first_db.name
            log.info(f"Using default database: {self.current_db_name}")
        elif self.db_url:
            # Extract database name from URL
            if "sqlite:///" in self.db_url:
                db_path = self.db_url.replace("sqlite:///", "")
                self.current_db_name = Path(db_path).stem
            else:
                self.current_db_name = "custom_db"
        else:
            raise ValueError("No databases found in the data directory")
        
        # Use the specified model_id or fallback if not available
        self.current_model_id = self.model_id
        
        # Initialize agent with available model
        self.initialize_agent()
        
        # Get the schema for the current database
        self.update_db_connection(self.db_url)
    
    def check_ollama_availability(self):
        """Check if Ollama is available locally or remotely."""
        # First try local Ollama
        try:
            import subprocess
            result = subprocess.run(
                ["which", "ollama"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
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
    
    def _try_remote_ollama(self):
        """Try to connect to remote Ollama server."""
        self.using_local_ollama = False
        self.ollama_mode = "remote"
        # Use the provided remote host or default
        self.model_discovery = OllamaDiscovery(ollama_host=self.ollama_host)
        try:
            self.models = self.model_discovery.discover_models()
            self.ollama_available = True
            log.info(f"Connected to remote Ollama at {self.ollama_host}")
            log.info(f"Found {len(self.models)} remote models")
        except Exception as e:
            log.warning(f"Failed to discover remote Ollama models: {e}")
            self.ollama_available = False
    
    def initialize_agent(self):
        """Initialize the agent with the current model.
        
        If the specified model is not available, it will try a default.
        """
        # Determine if we need to pull the model for local Ollama
        if self.using_local_ollama and self.ollama_available:
            try:
                # Check if we need to pull the model
                if self.current_model_id not in self.models:
                    log.info(f"Model {self.current_model_id} not found locally. Attempting to pull...")
                    import subprocess
                    result = subprocess.run(
                        ["ollama", "pull", self.current_model_id],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=600  # Allow up to 10 minutes for model download
                    )
                    if result.returncode == 0:
                        log.info(f"Successfully pulled model {self.current_model_id}")
                        # Refresh model list
                        self.models = self.model_discovery.discover_models()
                    else:
                        log.error(f"Failed to pull model {self.current_model_id}: {result.stderr}")
            except Exception as e:
                log.error(f"Error pulling model: {e}")
        
        try:
            # Create the Ollama model with appropriate options for mode
            if self.using_local_ollama:
                # Use local Ollama
                self.ollama_model = Ollama(
                    id=self.current_model_id,
                    base_url="http://localhost:11434"
                )
                log.info(f"Using local model: {self.current_model_id}")
            else:
                # Use remote Ollama
                self.ollama_model = Ollama(
                    id=self.current_model_id,
                    base_url=self.ollama_host
                )
                log.info(f"Using remote model: {self.current_model_id} from {self.ollama_host}")
            
            self.agent_name = "text2sql"
        
        except Exception as e:
            log.error(f"Failed to initialize model {self.current_model_id}: {e}")
            # Try a fallback if the current model isn't available
            fallback_models = [
                "qwen2.5-coder:1.5b",  # Try smaller model first
                "qwen2.5-coder:0.5b",  # Even smaller
                "llama3:8b",
                "phi3:mini"
            ]
            
            for fallback in fallback_models:
                try:
                    log.info(f"Trying fallback model: {fallback}")
                    
                    # For local Ollama, try to pull the model if needed
                    if self.using_local_ollama and fallback not in self.models:
                        try:
                            import subprocess
                            log.info(f"Pulling fallback model {fallback}...")
                            result = subprocess.run(
                                ["ollama", "pull", fallback],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=600
                            )
                            if result.returncode != 0:
                                log.error(f"Failed to pull fallback model {fallback}")
                                continue
                        except Exception:
                            continue
                    
                    # Initialize the model
                    if self.using_local_ollama:
                        self.ollama_model = Ollama(id=fallback, base_url="http://localhost:11434")
                    else:
                        self.ollama_model = Ollama(id=fallback, base_url=self.ollama_host)
                    
                    self.current_model_id = fallback
                    break
                except Exception:
                    continue
            
            if not hasattr(self, 'ollama_model'):
                log.error("Could not initialize any model")
                raise ValueError("No Ollama models available")
    
    def update_db_connection(self, db_url: str) -> None:
        """Update the database connection and refresh the agent.
        
        Args:
            db_url: The new database URL
        """
        self.db_url = db_url
        
        # Extract database name from URL
        if "sqlite:///" in self.db_url:
            db_path = self.db_url.replace("sqlite:///", "")
            self.current_db_name = Path(db_path).stem
        else:
            self.current_db_name = "custom_db"
        
        # Get schema from the discovery tool if available
        if self.current_db_name in self.databases:
            schema = self.db_discovery.get_database_schema(self.current_db_name)
        else:
            # If not in the discovery tool, try to get schema directly
            engine = create_engine(self.db_url)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Placeholder for schema if we can't get it directly
            schema = f"Database tables: {', '.join(tables)}"
        
        # Update the agent instructions with the new schema
        instructions = TEXT2SQL_TEMPLATE.format(schema=schema)
        
        # Instantiate the agent with the updated schema
        self.text2sql_agent = Agent(
            model=self.ollama_model, 
            name=self.agent_name, 
            role="Text to SQL Agent",
            instructions=[instructions], 
            show_tool_calls=True
        )
        
        # Instantiate the SQLTools
        self.engine = create_engine(self.db_url)
        self.tools = SQLTools(db_engine=self.engine)
        
        log.info(f"Connected to database: {self.current_db_name} with {self.db_url}")

    def write_query(self, question: str) -> str:
        """ Run the agent and return the sql query
        
        Args:
            question (str): question
        Returns:
            sql_query (str): sql query
        """
        response = self.text2sql_agent.run(question)
        sql_query = response.content
        return sql_query

    def execute_query(self, sql_query: str) -> str:
        """ Run the sql query 
        
        Args:
            sql_query (str): sql query
        Returns:
            results: Results as HTML
        """
        try:
            data = self.tools.run_sql(sql=sql_query)
            df = pd.DataFrame(data)
            if df.empty:
                return "No data found"
            else:
                return df.to_html()
        except Exception as e:
            log.error(f"Error executing query: {e}")
            return f"Error executing query: {str(e)}"

    def request(self, question: str) -> Tuple[str, str]:
        """ Run the agent and return the answer.
        
        Args:
            question (str): Natural language question
            
        Returns:
            Tuple of (sql_query, answer)
        """
        log.info(f"Writing SQL query for the question: {question}")
        sql_query = self.write_query(question)
        log.info(f"Executing the SQL query: {sql_query}")
        answer = self.execute_query(sql_query)
        return sql_query, answer
    
    def get_database_list(self) -> Dict[str, DatabaseInfo]:
        """Get the list of available databases.
        
        Returns:
            Dict of database information
        """
        # Refresh the database discovery
        self.databases = self.db_discovery.discover_databases()
        return self.databases
    
    def get_database_selector_html(self) -> str:
        """Get HTML for the database selector UI.
        
        Returns:
            HTML for the database selector
        """
        options = ""
        for db_name, db_info in self.databases.items():
            selected = "selected" if db_name == self.current_db_name else ""
            options += f'<option value="{db_name}" {selected}>{db_name}</option>\n'
        
        schema = ""
        if self.current_db_name in self.databases:
            schema = self.db_discovery.get_formatted_schema(self.current_db_name)
        
        return DATABASE_SELECT_TEMPLATE.format(options=options, schema=schema)
    
    def set_active_database(self, db_name: str) -> bool:
        """Set the active database.
        
        Args:
            db_name: Name of the database to use
            
        Returns:
            True if successful, False otherwise
        """
        if db_name not in self.databases:
            log.error(f"Database {db_name} not found")
            return False
        
        self.update_db_connection(self.databases[db_name].url)
        return True
        
    def get_model_list(self) -> Dict[str, ModelInfo]:
        """Get the list of available models.
        
        Returns:
            Dict of model information
        """
        # Refresh the model discovery
        try:
            self.models = self.model_discovery.discover_models()
            self.ollama_available = True
        except Exception as e:
            log.warning(f"Failed to discover Ollama models: {e}")
            self.ollama_available = False
            
        return self.models
    
    def get_model_selector_html(self) -> str:
        """Get HTML for the model selector UI.
        
        Returns:
            HTML for the model selector
        """
        if not self.ollama_available:
            return "<div class='error'>Ollama not available</div>"
            
        options = ""
        for model_name in self.models:
            selected = "selected" if model_name == self.current_model_id else ""
            options += f'<option value="{model_name}" {selected}>{model_name}</option>\n'
        
        # Get info about current model
        model_info = ""
        if self.current_model_id in self.models:
            model = self.models[self.current_model_id]
            model_info = f"Model: {model.name}\nSize: {model.size}\nLast Modified: {model.modified}"
        
        return MODEL_SELECT_TEMPLATE.format(options=options, info=model_info)
    
    def set_active_model(self, model_name: str) -> bool:
        """Set the active model.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if successful, False otherwise
        """
        # Handle special case for switching Ollama mode
        if model_name.lower() == "local":
            return self.switch_to_local_mode()
        elif model_name.lower() == "remote":
            return self.switch_to_remote_mode()
        
        # For regular model switching:
        # First check if the model exists (or can be pulled in local mode)
        model_exists = (model_name in self.models or 
                       self.model_discovery.get_model_details(model_name) is not None)
        
        if not model_exists and self.using_local_ollama:
            # If in local mode and model not found, try to pull it
            try:
                log.info(f"Model {model_name} not found locally. Attempting to pull...")
                import subprocess
                result = subprocess.run(
                    ["ollama", "pull", model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=600
                )
                if result.returncode == 0:
                    log.info(f"Successfully pulled model {model_name}")
                    # Refresh model list
                    self.models = self.model_discovery.discover_models()
                    model_exists = True
                else:
                    log.error(f"Failed to pull model {model_name}: {result.stderr}")
            except Exception as e:
                log.error(f"Error pulling model: {e}")
        
        if not model_exists:
            log.error(f"Model {model_name} not found and could not be pulled")
            return False
        
        try:
            # Try to initialize with the new model
            old_model_id = self.current_model_id
            self.current_model_id = model_name
            
            # Create a new Ollama model with appropriate settings
            if self.using_local_ollama:
                self.ollama_model = Ollama(id=model_name, base_url="http://localhost:11434")
            else:
                self.ollama_model = Ollama(id=model_name, base_url=self.ollama_host)
            
            # Reinitialize the agent with the new model
            schema = self.db_discovery.get_database_schema(self.current_db_name)
            instructions = TEXT2SQL_TEMPLATE.format(schema=schema)
            
            self.text2sql_agent = Agent(
                model=self.ollama_model, 
                name=self.agent_name, 
                role="Text to SQL Agent",
                instructions=[instructions], 
                show_tool_calls=True
            )
            
            log.info(f"Switched model from {old_model_id} to {model_name}")
            return True
        except Exception as e:
            log.error(f"Failed to set model {model_name}: {e}")
            # Revert to previous model
            try:
                self.current_model_id = old_model_id
                if self.using_local_ollama:
                    self.ollama_model = Ollama(id=old_model_id, base_url="http://localhost:11434")
                else:
                    self.ollama_model = Ollama(id=old_model_id, base_url=self.ollama_host)
            except Exception:
                log.error(f"Failed to revert to previous model {old_model_id}")
            return False
    
    def switch_to_local_mode(self) -> bool:
        """Switch to using local Ollama instance."""
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
                timeout=2
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
                            timeout=600
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
            
            # Initialize agent with the new model
            try:
                self.initialize_agent()
                log.info(f"Switched to local mode using model {self.current_model_id}")
                return True
            except Exception as e:
                log.error(f"Failed to initialize agent in local mode: {e}")
                # Revert to previous mode
                self.using_local_ollama = False
                self.ollama_mode = old_mode
                self.ollama_host = old_host
                self.current_model_id = old_model_id
                return False
                
        except Exception as e:
            log.error(f"Error switching to local mode: {e}")
            return False
    
    def switch_to_remote_mode(self) -> bool:
        """Switch to using remote Ollama instance."""
        if not self.using_local_ollama:
            log.info("Already in remote mode")
            return True
        
        # Save old settings
        old_mode = self.ollama_mode
        old_using_local = self.using_local_ollama
        old_model_id = self.current_model_id
        
        try:
            # Switch to remote mode
            self.using_local_ollama = False
            self.ollama_mode = "remote"
            # Use the previously configured remote host or default
            if not self.ollama_host or self.ollama_host == "http://localhost:11434":
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
                    # Use a common model name and hope it exists
                    self.current_model_id = "qwen2.5-coder:7b"
            else:
                # Keep using the same model
                self.current_model_id = old_model_id
            
            # Initialize agent with the new model
            try:
                self.initialize_agent()
                log.info(f"Switched to remote mode using model {self.current_model_id}")
                return True
            except Exception as e:
                log.error(f"Failed to initialize agent in remote mode: {e}")
                # Revert to previous mode
                self.using_local_ollama = old_using_local
                self.ollama_mode = old_mode
                self.current_model_id = old_model_id
                return False
                
        except Exception as e:
            log.error(f"Error switching to remote mode: {e}")
            return False