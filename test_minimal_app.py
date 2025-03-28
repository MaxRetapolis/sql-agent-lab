import os
import sys
import time
import subprocess

def test_sql_query_generation():
    """Test the SQL query generation using local Ollama."""
    print("\n=== Testing SQL Query Generation with Ollama ===")
    
    print("1. Checking Ollama service...")
    # Check if Ollama is running
    result = subprocess.run(
        ["pgrep", "-f", "ollama"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        timeout=2
    )
    
    if result.returncode != 0:
        print("❌ Ollama service is not running")
        print("Starting Ollama service...")
        try:
            subprocess.Popen(
                ["/home/coder/bin/ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Waiting for Ollama to start...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Failed to start Ollama service: {e}")
            return False
    else:
        print(f"✅ Ollama service is running (PID: {result.stdout.strip()})")
    
    # Verify model availability
    print("\n2. Checking model availability...")
    result = subprocess.run(
        ["/home/coder/bin/ollama", "list"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        timeout=5
    )
    
    if result.returncode != 0:
        print(f"❌ Failed to list models: {result.stderr}")
        return False
    
    model_name = "qwen2.5-coder:0.5b"
    if model_name not in result.stdout:
        print(f"❌ Required model {model_name} not found")
        return False
    
    print(f"✅ Model {model_name} is available")
    
    # Test database connectivity
    print("\n3. Testing database connectivity...")
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
        
        # Close the connection
        conn.close()
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False
    
    # Test direct Ollama interaction for query generation
    print("\n4. Testing SQL query generation with Ollama...")
    prompt = f"""
Generate a SQL query to list all products from the shop database.
The database has the following tables:
- Customers: id, first_name, last_name, email, phone, address
- Products: id, name, description, price, stock, category
- Orders: id, customer_id, order_date, total_amount
- OrderDetails: id, order_id, product_id, quantity, price

Write a SQL query that will list the name, price, and category of all products.
"""
    
    try:
        process = subprocess.Popen(
            ["/home/coder/bin/ollama", "run", model_name, prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Set a timeout for the process
        timeout = 30  # seconds
        start_time = time.time()
        
        # Collect output with timeout
        output = ""
        while process.poll() is None and time.time() - start_time < timeout:
            if process.stdout:
                line = process.stdout.readline()
                if line:
                    output += line
                    print(f"Output: {line.strip()}")
                else:
                    time.sleep(0.1)
        
        # Check if we timed out
        if process.poll() is None:
            print("❌ Timed out waiting for response")
            process.terminate()
            return False
        
        # Check if there was an error
        if process.returncode != 0:
            stderr = process.stderr.read()
            print(f"❌ Error generating SQL query: {stderr}")
            return False
        
        # Success!
        print("\n✅ Successfully generated SQL query with Ollama")
        
        # Execute the query if it contains valid SQL
        if "SELECT" in output.upper() and "FROM" in output.upper() and "Products" in output:
            print("\n5. Testing execution of the generated query...")
            try:
                # Extract SQL from the response
                sql_lines = []
                for line in output.splitlines():
                    if "SELECT" in line.upper() or "FROM" in line.upper() or "WHERE" in line.upper():
                        sql_lines.append(line)
                
                sql_query = " ".join(sql_lines)
                print(f"Extracted SQL query: {sql_query}")
                
                # Execute the query
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute(sql_query)
                results = cursor.fetchall()
                
                print(f"Query returned {len(results)} rows")
                for row in results[:3]:  # Show first 3 rows
                    print(f"  {row}")
                
                conn.close()
                print("\n✅ Successfully executed the generated SQL query")
            except Exception as e:
                print(f"❌ Error executing SQL query: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing SQL generation: {e}")
        return False

if __name__ == "__main__":
    test_sql_query_generation()