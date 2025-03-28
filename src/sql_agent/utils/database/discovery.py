"""Database discovery utilities."""
import os
from typing import Dict, List, Tuple
from pathlib import Path
import sqlite3
from sqlalchemy import create_engine, inspect
from dataclasses import dataclass
from sql_agent.utils import logger

log = logger.get_logger(__name__)


@dataclass
class DatabaseInfo:
    """Information about a discovered database."""
    name: str
    path: str
    url: str
    tables: List[str]
    column_info: Dict[str, List[Tuple[str, str]]]


class DatabaseDiscovery:
    """Utility for discovering SQLite databases in a directory."""
    
    def __init__(self, data_dir: str = "app/data"):
        """Initialize the database discovery utility.
        
        Args:
            data_dir: Directory containing the database files
        """
        self.data_dir = data_dir
        self.databases: Dict[str, DatabaseInfo] = {}
        
    def discover_databases(self) -> Dict[str, DatabaseInfo]:
        """Discover all SQLite databases in the data directory.
        
        Returns:
            Dict mapping database names to DatabaseInfo objects
        """
        log.info(f"Discovering databases in {self.data_dir}")
        self.databases = {}
        
        # Ensure data directory exists
        data_path = Path(self.data_dir)
        if not data_path.exists():
            log.warning(f"Data directory {self.data_dir} does not exist")
            return self.databases
        
        # Find all .db files
        for file_path in data_path.glob("*.db"):
            db_name = file_path.stem
            db_path = str(file_path)
            db_url = f"sqlite:///{db_path}"
            
            try:
                # Connect to database and get table info
                engine = create_engine(db_url)
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                # Get column info for each table
                column_info = {}
                for table in tables:
                    columns = inspector.get_columns(table)
                    column_info[table] = [(col["name"], str(col["type"])) for col in columns]
                
                # Store database info
                self.databases[db_name] = DatabaseInfo(
                    name=db_name,
                    path=db_path,
                    url=db_url,
                    tables=tables,
                    column_info=column_info
                )
                log.info(f"Discovered database {db_name} with tables: {tables}")
            except Exception as e:
                log.error(f"Error inspecting database {db_path}: {e}")
        
        return self.databases
    
    def get_database_schema(self, db_name: str) -> str:
        """Get the schema of a database in SQL CREATE TABLE format.
        
        Args:
            db_name: Name of the database
            
        Returns:
            SQL CREATE TABLE statements for the database
        """
        if db_name not in self.databases:
            return f"Database {db_name} not found"
        
        db_info = self.databases[db_name]
        schema = []
        
        try:
            # Connect to SQLite database directly to get schema
            conn = sqlite3.connect(db_info.path)
            cursor = conn.cursor()
            
            for table in db_info.tables:
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                create_stmt = cursor.fetchone()
                if create_stmt and create_stmt[0]:
                    schema.append(create_stmt[0])
            
            conn.close()
        except Exception as e:
            log.error(f"Error getting schema for {db_name}: {e}")
            return f"Error: {e}"
        
        return "\n\n".join(schema)
    
    def get_formatted_schema(self, db_name: str) -> str:
        """Get a formatted description of the database schema.
        
        Args:
            db_name: Name of the database
            
        Returns:
            Formatted description of the database schema
        """
        if db_name not in self.databases:
            return f"Database {db_name} not found"
        
        db_info = self.databases[db_name]
        schema_lines = [f"Database: {db_name}"]
        
        for table in db_info.tables:
            schema_lines.append(f"\nTable: {table}")
            schema_lines.append("-" * (len(table) + 7))
            
            for column_name, column_type in db_info.column_info[table]:
                schema_lines.append(f"  {column_name} ({column_type})")
        
        return "\n".join(schema_lines)