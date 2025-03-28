#!/usr/bin/env python3
"""
Test script to measure model response times with various timeouts.
"""
import subprocess
import time
import sys

def test_model(model_name, prompt, timeout=300, show_output=True):
    """Test a model with the given prompt and timeout."""
    print(f"Testing {model_name} with {timeout}s timeout...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ['/home/coder/bin/ollama', 'run', model_name, prompt, '--nowordwrap'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        print(f"Time elapsed: {elapsed:.2f} seconds")
        
        if result.returncode == 0:
            print(f"SUCCESS! Output received in {elapsed:.2f} seconds")
            if show_output:
                print("\nOutput:")
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            return True, elapsed
        else:
            print(f"ERROR: {result.stderr}")
            return False, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"TIMEOUT after {elapsed:.2f} seconds")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"EXCEPTION: {e}")
        return False, elapsed

def main():
    """Main function to run the tests."""
    prompt = "Write this SQL query: SELECT COUNT(*) FROM users;"
    models = [
        "phi:latest",
        "deepseek-r1:1.5b"
    ]
    
    results = {}
    
    for model in models:
        success, time_taken = test_model(model, prompt, timeout=120)
        results[model] = {
            "success": success,
            "time": time_taken
        }
        print("\n" + "-"*50 + "\n")
    
    # Print summary
    print("\nSUMMARY:")
    print("-"*50)
    for model, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED/TIMEOUT"
        print(f"{model}: {status} - {result['time']:.2f} seconds")

if __name__ == "__main__":
    main()