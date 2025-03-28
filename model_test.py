import subprocess
import json
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_model_inference(model_name):
    """Test if a model can run a basic inference without tensor errors."""
    try:
        logger.info(f"Testing model: {model_name}")
        # Use a simple prompt that should work with any model
        prompt = "Generate a short SQL query that selects all users"
        
        # Run inference using ollama CLI with explicit path
        result = subprocess.run(
            ["/home/coder/bin/ollama", "run", model_name, prompt, "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Success: {model_name} generated output without errors")
            return True, result.stdout, None
        else:
            error = result.stderr
            logger.error(f"❌ Failed: {model_name} returned error: {error}")
            tensor_error = "tensor" in error and "not found" in error
            return False, None, (error, tensor_error)
    except subprocess.TimeoutExpired:
        logger.error(f"⚠️ Timeout: {model_name} took too long to respond")
        return False, None, ("Timeout", False)
    except Exception as e:
        logger.error(f"⚠️ Exception: {model_name} raised error: {e}")
        return False, None, (str(e), False)

def main():
    try:
        # Get list of available models - Ollama list format parsing
        result = subprocess.run(
            ["/home/coder/bin/ollama", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        # Parse the table output format (NAME SIZE MODIFIED)
        models = []
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Skip header line
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    model_name = parts[0]
                    models.append(model_name)
        
        if not models:
            logger.error("No models found")
            return
        
        logger.info(f"Found {len(models)} models: {', '.join(models)}")
        
        # Test each model
        results = {}
        tensor_error_models = []
        working_models = []
        
        for model in models:
            success, output, error = test_model_inference(model)
            results[model] = {
                "success": success,
                "output": output,
                "error": error
            }
            
            if success:
                working_models.append(model)
            elif error and error[1]:  # Has tensor error
                tensor_error_models.append(model)
            
            # Add a small delay between tests
            time.sleep(1)
        
        # Print summary
        print("\n=== Test Results ===")
        print(f"Working models: {len(working_models)}/{len(models)}")
        for model in working_models:
            print(f"✅ {model}")
            
        print(f"\nModels with tensor errors: {len(tensor_error_models)}/{len(models)}")
        for model in tensor_error_models:
            print(f"❌ {model}")
            
        print(f"\nOther failing models: {len(models) - len(working_models) - len(tensor_error_models)}/{len(models)}")
        for model in models:
            if model not in working_models and model not in tensor_error_models:
                error_info = results[model]["error"]
                print(f"⚠️ {model}: {error_info[0] if error_info else 'Unknown error'}")
        
        # Write results to file for future reference
        with open("model_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
            
        print(f"\nDetailed results saved to model_test_results.json")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == "__main__":
    main()