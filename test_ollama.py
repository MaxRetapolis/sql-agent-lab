import os
import sys

# Add the src directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# Import the Text2SQLAgent
try:
    from sql_agent.agno_agent import Text2SQLAgent
    print("Successfully imported Text2SQLAgent")
except ImportError as e:
    print(f"Failed to import Text2SQLAgent: {e}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:0.5b")

def main():
    """Test the Ollama integration."""
    print("\n=== Testing Ollama Integration ===")
    print(f"Ollama Host: {OLLAMA_HOST}")
    print(f"Default Model: {DEFAULT_MODEL}")
    
    try:
        # Create agent with default settings (should try local first)
        agent = Text2SQLAgent(ollama_host=OLLAMA_HOST, model_id=DEFAULT_MODEL)
        
        # Show agent status
        print("\n=== Agent Status ===")
        print(f"Ollama Mode: {agent.ollama_mode}")
        print(f"Ollama Host: {agent.ollama_host}")
        print(f"Ollama Available: {agent.ollama_available}")
        print(f"Current Model: {agent.current_model_id}")
        
        # List available models
        print("\n=== Available Models ===")
        for name, info in agent.models.items():
            print(f"- {name}")
        
        # List available databases
        print("\n=== Available Databases ===")
        for name, info in agent.databases.items():
            print(f"- {name}")
        
        # Try a simple query if both model and database are available
        if agent.ollama_available and agent.databases:
            db_name = next(iter(agent.databases.keys()))
            agent.set_active_database(db_name)
            
            print(f"\n=== Testing Query on {db_name} ===")
            try:
                question = "List all tables in the database"
                print(f"Question: {question}")
                
                sql_query = agent.write_query(question)
                print(f"SQL Query: {sql_query}")
                
                result = agent.execute_query(sql_query)
                print(f"Result: {result}")
                
                print("\nTest completed successfully!")
            except Exception as e:
                print(f"Error testing query: {e}")
        else:
            if not agent.ollama_available:
                print("\nSkipping query test - Ollama not available")
            if not agent.databases:
                print("\nSkipping query test - No databases found")
    
    except Exception as e:
        print(f"Error initializing agent: {e}")

if __name__ == "__main__":
    main()