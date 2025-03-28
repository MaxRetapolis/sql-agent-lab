import os
import sqlite3
from pathlib import Path

def test_sqlite_connectivity():
    """Test connectivity to SQLite databases in the data directory."""
    print("\n=== Testing SQLite Database Connectivity ===")
    
    data_dir = "app/data"
    print(f"Scanning directory: {data_dir}")
    
    # Find all SQLite database files
    db_files = []
    for file in Path(data_dir).glob("**/*.db"):
        db_files.append(str(file))
    
    if not db_files:
        print("No SQLite database files found")
        return False
    
    print(f"Found {len(db_files)} database files:")
    for db_file in db_files:
        print(f"- {db_file}")
    
    # Test connecting to each database
    for db_file in db_files:
        print(f"\nTesting connection to {db_file}...")
        try:
            # Connect to the database
            conn = sqlite3.connect(db_file)
            print("✅ Connected successfully")
            
            # Get list of tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if tables:
                print(f"Tables found: {len(tables)}")
                for table in tables:
                    print(f"- {table[0]}")
                    
                    # Get schema for the table
                    cursor.execute(f"PRAGMA table_info({table[0]})")
                    columns = cursor.fetchall()
                    print(f"  Columns: {len(columns)}")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    row_count = cursor.fetchone()[0]
                    print(f"  Rows: {row_count}")
                    
                    # Sample data if there are rows
                    if row_count > 0:
                        cursor.execute(f"SELECT * FROM {table[0]} LIMIT 3")
                        sample_data = cursor.fetchall()
                        print(f"  Sample data: {sample_data}")
            else:
                print("No tables found in the database")
            
            # Close the connection
            conn.close()
            
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
    
    return True

if __name__ == "__main__":
    test_sqlite_connectivity()