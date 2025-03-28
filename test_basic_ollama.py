import os
import subprocess
import time
import json

def test_local_ollama():
    """Test connectivity to local Ollama installation."""
    print("\n=== Testing Local Ollama ===")
    
    # Check if Ollama binary exists
    try:
        result = subprocess.run(
            ["which", "ollama"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print(f"✅ Local Ollama found at: {result.stdout.strip()}")
        else:
            print("❌ Local Ollama installation not found")
            return False
    except Exception as e:
        print(f"❌ Error checking for local Ollama: {e}")
        return False
    
    # Check if Ollama service is running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ollama"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print(f"✅ Ollama service is running (PID: {result.stdout.strip()})")
        else:
            print("❌ Ollama service is not running")
            # Try to start Ollama service
            try:
                print("Starting Ollama service...")
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("✅ Ollama service started")
                # Wait for the service to initialize
                print("Waiting for Ollama service to initialize...")
                time.sleep(5)
            except Exception as e:
                print(f"❌ Failed to start Ollama service: {e}")
                return False
    except Exception as e:
        print(f"❌ Error checking if Ollama service is running: {e}")
        return False
    
    # Wait for Ollama to become ready
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Checking if Ollama is ready (attempt {attempt+1}/{max_retries})...")
            result = subprocess.run(
                ["ollama", "list"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✅ Ollama is ready")
                break
            else:
                print(f"Ollama not ready yet: {result.stderr}")
                if attempt < max_retries - 1:
                    print("Waiting 5 seconds before retrying...")
                    time.sleep(5)
                else:
                    print("❌ Ollama failed to become ready after multiple attempts")
                    return False
        except Exception as e:
            print(f"Error checking Ollama readiness: {e}")
            if attempt < max_retries - 1:
                print("Waiting 5 seconds before retrying...")
                time.sleep(5)
            else:
                print("❌ Ollama failed to become ready after multiple attempts")
                return False
    
    # List available models
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
            if "qwen2.5-coder:0.5b" in result.stdout:
                print("✅ Required model qwen2.5-coder:0.5b is available")
            else:
                print("❌ Required model qwen2.5-coder:0.5b is not available")
                try:
                    print("Pulling required model...")
                    pull_result = subprocess.run(
                        ["ollama", "pull", "qwen2.5-coder:0.5b"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=600
                    )
                    if pull_result.returncode == 0:
                        print("✅ Successfully pulled model qwen2.5-coder:0.5b")
                    else:
                        print(f"❌ Failed to pull model: {pull_result.stderr}")
                except Exception as e:
                    print(f"❌ Error pulling model: {e}")
        else:
            print(f"❌ Failed to list models: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return False
    
    # Test generating a simple SQL query
    try:
        print("\n=== Testing SQL Generation ===")
        print("Query: List all tables in the database")
        
        # Run a simple generation test
        cmd = ["ollama", "run", "qwen2.5-coder:0.5b", 
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
            print("\n✅ SQL generation successful")
            return True
        else:
            print(f"❌ Failed to generate SQL: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing SQL generation: {e}")
        return False

if __name__ == "__main__":
    test_local_ollama()