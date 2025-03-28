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
from sql_agent.utils.models.discovery import ModelInfo
from sql_agent.utils.models.manager import ModelManager, ModelManagerConfig
import pandas as pd

log = logger.get_logger(__name__)


@dataclass
class Text2SQLAgent:
    """ Text to SQL Agent to convert natural language to SQL """
    db_url: Optional[str] = None
    data_dir: str = "app/data"
    model_id: str = "phi:latest"  # Changed default to phi:latest as most reliable
    ollama_host: Optional[str] = None
    
    def __post_init__(self):
        # Initialize database discovery
        self.db_discovery = DatabaseDiscovery(self.data_dir)
        self.databases = self.db_discovery.discover_databases()
        
        # Initialize model manager
        model_config = ModelManagerConfig(
            ollama_host=self.ollama_host,
            default_model_id=self.model_id,
            use_remote_models=True
        )
        self.model_manager = ModelManager(config=model_config)
        
        # Initialize model-related properties
        self.using_local_ollama = self.model_manager.using_local_ollama
        self.ollama_mode = self.model_manager.ollama_mode
        self.ollama_host = self.model_manager.ollama_host
        self.models = self.model_manager.models
        self.current_model_id = self.model_manager.current_model_id
        self.ollama_available = self.model_manager.ollama_available
        
        # Remote model properties
        self.remote_models = getattr(self.model_manager, 'remote_models', {})
        self.using_remote_model = getattr(self.model_manager, 'using_remote_model', False)
        self.remote_model_available = getattr(self.model_manager, 'remote_model_available', False)
        
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
        
        # Initialize agent with available model
        self.initialize_agent()
        
        # Get the schema for the current database
        self.update_db_connection(self.db_url)
    
    def check_ollama_availability(self):
        """Check if Ollama is available locally or remotely.
        
        Returns:
            True if available, False otherwise
        """
        # Just delegate to model manager
        self.ollama_available = self.model_manager.check_ollama_availability()
        
        # Update our properties to match model manager
        self.using_local_ollama = self.model_manager.using_local_ollama
        self.ollama_mode = self.model_manager.ollama_mode
        self.ollama_host = self.model_manager.ollama_host
        self.models = self.model_manager.models
        
        return self.ollama_available
    
    def initialize_agent(self):
        """Initialize the agent with the current model.
        
        If the specified model is not available, it will try a fallback.
        """
        # Check if we're using a remote model (like Haiku)
        if hasattr(self, 'using_remote_model') and self.using_remote_model:
            # For remote models, just set a flag - we'll handle the actual API call in request()
            log.info(f"Using remote model: {self.current_model_id}")
            self.agent_name = "text2sql_remote"
            return
            
        # Get the best model from model manager for local Ollama models
        self.current_model_id, is_fallback = self.model_manager.get_best_model()
        
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
            # Check if we have remote models available as fallback
            if hasattr(self, 'remote_model_available') and self.remote_model_available:
                log.warning(f"Failed to initialize local model. Falling back to remote model.")
                self.use_remote_model(self.current_remote_model)
                return
            
            log.error(f"Failed to initialize model {self.current_model_id}: {e}")
            raise ValueError("Failed to initialize model. No working models available.")
    
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
        
        # Check if we're using a remote model
        if hasattr(self, 'using_remote_model') and self.using_remote_model:
            # Extract the remote model ID from the current_model_id
            if ":" in self.current_model_id:
                remote_model_id = self.current_model_id.split(":", 1)[1]
            else:
                remote_model_id = self.current_remote_model
                
            # Get the provider for this model
            if remote_model_id in self.remote_models:
                provider = self.remote_models[remote_model_id]
                
                # Get database schema
                schema = self.db_discovery.get_database_schema(self.current_db_name)
                
                # Create prompt for the remote model
                prompt = TEXT2SQL_TEMPLATE.format(
                    schema=schema,
                    question=question
                )
                
                # Call the remote API
                try:
                    log.info(f"Using remote model {remote_model_id} to write SQL")
                    response = provider.generate(prompt)
                    
                    if response:
                        # Extract SQL query from response
                        if "```sql" in response:
                            # Extract SQL from markdown code block
                            sql_parts = response.split("```sql", 1)
                            if len(sql_parts) > 1:
                                sql_query = sql_parts[1].split("```", 1)[0].strip()
                            else:
                                sql_query = response.strip()
                        else:
                            # Just use the whole response
                            sql_query = response.strip()
                            
                        log.info(f"Executing the SQL query: {sql_query}")
                        answer = self.execute_query(sql_query)
                        return sql_query, answer
                    else:
                        log.error("Remote model returned empty response")
                        raise ValueError("Remote model failed to generate SQL")
                except Exception as e:
                    log.error(f"Error using remote model: {e}")
                    # Fall back to local model
                    log.info("Falling back to local model")
                    self.use_local_model()
            else:
                log.error(f"Remote model {remote_model_id} not found")
                # Fall back to local model
                log.info("Falling back to local model")
                self.use_local_model()
        
        # Use the local Ollama model
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
        # Refresh the model discovery through model manager
        self.models = self.model_manager.get_model_list()
        self.ollama_available = self.model_manager.ollama_available
            
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
        
        # Check if the model exists or can be pulled
        if model_name not in self.models and self.model_manager.using_local_ollama:
            # Try to pull the model
            if not self.model_manager.pull_model(model_name):
                return False
        
        try:
            # Save old model ID
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
        # Use model manager to switch to local
        success = self.model_manager.switch_to_local_mode()
        
        if success:
            # Update our local properties to match manager
            self.using_local_ollama = self.model_manager.using_local_ollama
            self.ollama_mode = self.model_manager.ollama_mode
            self.ollama_host = self.model_manager.ollama_host
            self.current_model_id = self.model_manager.current_model_id
            self.models = self.model_manager.models
            self.ollama_available = self.model_manager.ollama_available
            
            # Reinitialize agent with new model
            self.initialize_agent()
        
        return success
    
    def switch_to_remote_mode(self) -> bool:
        """Switch to using remote Ollama instance."""
        # Use model manager to switch to remote
        success = self.model_manager.switch_to_remote_mode()
        
        if success:
            # Update our local properties to match manager
            self.using_local_ollama = self.model_manager.using_local_ollama
            self.ollama_mode = self.model_manager.ollama_mode
            self.ollama_host = self.model_manager.ollama_host
            self.current_model_id = self.model_manager.current_model_id
            self.models = self.model_manager.models
            self.ollama_available = self.model_manager.ollama_available
            
            # Reinitialize agent with new model
            self.initialize_agent()
        
        return success
    
    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Set API key for a remote model provider.
        
        Args:
            provider: Provider name or model ID
            api_key: API key
            
        Returns:
            True if successful, False otherwise
        """
        success = self.model_manager.set_api_key(provider, api_key)
        
        if success:
            # Update our local properties
            self.remote_models = getattr(self.model_manager, 'remote_models', {})
            self.remote_model_available = getattr(self.model_manager, 'remote_model_available', False)
        
        return success
    
    def use_remote_model(self, model_id: str) -> bool:
        """Switch to using a remote model.
        
        Args:
            model_id: Remote model ID
            
        Returns:
            True if successful, False otherwise
        """
        success = self.model_manager.use_remote_model(model_id)
        
        if success:
            # Update our local properties
            self.using_remote_model = True
            self.current_model_id = self.model_manager.current_model_id
            
            # Reconfiguring the agent for remote model is nontrivial, so we'll need to handle this
            # differently from Ollama models. For now, just set a flag that we're using remote.
            
            # TODO: Implement remote model agent configuration
            log.info(f"Using remote model: {model_id}")
        
        return success
    
    def use_local_model(self) -> bool:
        """Switch back to using local Ollama model.
        
        Returns:
            True if successful, False otherwise
        """
        success = self.model_manager.use_local_model()
        
        if success:
            # Update our local properties
            self.using_remote_model = False
            self.current_model_id = self.model_manager.current_model_id
            
            # Reinitialize agent with local model
            self.initialize_agent()
        
        return success