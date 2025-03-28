import os
import sqlite3
import time

def test_direct_sql_execution():
    """Test direct SQL execution without using Ollama."""
    print("\n=== Testing Direct SQL Execution ===")
    
    # Test database connectivity
    print("\n1. Testing database connectivity...")
    db_file = "app/data/shop.db"
    try:
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Connected to database with {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("❌ No tables found in the database")
            return False
        
        # Test executing a predefined SQL query
        print("\n2. Executing SQL query...")
        sql_query = "SELECT name, price, category FROM Products"
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        print(f"Query returned {len(results)} rows")
        print("Sample results:")
        for row in results[:5]:  # Show first 5 rows
            print(f"  {row}")
        
        # Test another query
        print("\n3. Executing a more complex SQL query...")
        sql_query = """
        SELECT p.Name, p.Price, o.OrderDate, c.FirstName, c.LastName
        FROM Products p
        JOIN OrderDetails od ON p.ProductID = od.ProductID
        JOIN Orders o ON od.OrderID = o.OrderID
        JOIN Customers c ON o.CustomerID = c.CustomerID
        LIMIT 5
        """
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        print(f"Query returned {len(results)} rows")
        print("Sample results:")
        for row in results:
            print(f"  {row}")
        
        # Close the connection
        conn.close()
        print("\n✅ Successfully executed SQL queries")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_database_schema(db_file):
    """Get the schema of a SQLite database."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema = []
        for table in tables:
            table_name = table[0]
            schema.append(f"Table: {table_name}")
            
            # Get columns for this table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_info = []
            for col in columns:
                # col format: (cid, name, type, notnull, dflt_value, pk)
                col_name = col[1]
                col_type = col[2]
                is_pk = "PRIMARY KEY" if col[5] == 1 else ""
                col_info.append(f"  - {col_name} ({col_type}) {is_pk}")
            
            schema.extend(col_info)
            schema.append("")  # Empty line between tables
        
        conn.close()
        return "\n".join(schema)
    except Exception as e:
        return f"Error getting schema: {e}"

if __name__ == "__main__":
    db_file = "app/data/shop.db"
    
    print("Testing direct SQL execution")
    test_direct_sql_execution()
    
    print("\n=== Database Schema ===")
    schema = get_database_schema(db_file)
    print(schema)