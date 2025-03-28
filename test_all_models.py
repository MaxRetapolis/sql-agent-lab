import subprocess
import time

def test_model(model_name):
    """Test a specific Ollama model for SQL generation."""
    print(f"\n=== Testing {model_name} ===")
    
    # Test generating a simple SQL query
    try:
        print(f"Query: List all tables in the database using {model_name}")
        
        # Run a simple generation test
        cmd = ["ollama", "run", model_name, 
               "Generate a SQL query that lists all tables in a SQLite database"]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("\nGenerated SQL:")
            print(result.stdout)
            print(f"\n✅ {model_name} SQL generation successful")
            return True
        else:
            print(f"❌ Failed to generate SQL with {model_name}: {result.stderr}")
            # Check for tensor initialization error
            if "tensor" in result.stderr and "not found" in result.stderr:
                print(f"❌ MODEL HAS TENSOR INITIALIZATION ERROR: {model_name}")
            return False
    except Exception as e:
        print(f"❌ Error testing SQL generation with {model_name}: {e}")
        return False

def main():
    # Get list of available models
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("\n=== Available Models ===")
            print(result.stdout)
            
            # Extract model names
            models = []
            for line in result.stdout.splitlines()[1:]:  # Skip header line
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            
            print(f"\nFound {len(models)} models to test: {', '.join(models)}")
            
            # Test each model
            results = {}
            for model in models:
                results[model] = test_model(model)
                time.sleep(1)  # Add a small delay between tests
            
            # Print summary
            print("\n=== Model Test Summary ===")
            working_models = []
            failing_models = []
            
            for model, success in results.items():
                status = "✅ Works" if success else "❌ Fails"
                print(f"{model}: {status}")
                
                if success:
                    working_models.append(model)
                else:
                    failing_models.append(model)
            
            print(f"\nWorking models: {', '.join(working_models) if working_models else 'None'}")
            print(f"Failing models: {', '.join(failing_models) if failing_models else 'None'}")
            
        else:
            print(f"❌ Failed to list models: {result.stderr}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    main()