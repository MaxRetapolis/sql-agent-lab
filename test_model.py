import subprocess
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_model(model_name):
    """Test if a model can run a basic SQL generation without tensor errors."""
    try:
        logger.info(f"Testing model: {model_name}")
        
        # Use a simple SQL generation prompt
        prompt = "Generate a SQL query that selects all users from a users table"
        
        # Run inference with a longer timeout
        result = subprocess.run(
            ["/home/coder/bin/ollama", "run", model_name, prompt, "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # Give it up to 60 seconds
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Success: {model_name} generated output without errors")
            logger.info(f"Output: {result.stdout}")
            return True, result.stdout, None
        else:
            error = result.stderr
            logger.error(f"❌ Failed: {model_name} returned error:\n{error}")
            
            # Check for tensor initialization error
            tensor_error = "tensor" in error and "not found" in error
            if tensor_error:
                logger.error(f"🚫 Model has TENSOR INITIALIZATION ERROR")
            
            return False, None, (error, tensor_error)
    except subprocess.TimeoutExpired:
        logger.error(f"⚠️ Timeout: {model_name} took too long to respond")
        return False, None, ("Timeout", False)
    except Exception as e:
        logger.error(f"⚠️ Exception: {model_name} raised error: {e}")
        return False, None, (str(e), False)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_model.py <model_name>")
        print("Example: python3 test_model.py qwen2.5-coder:1.5b")
        
        # List available models
        logger.info("Available models:")
        result = subprocess.run(
            ["/home/coder/bin/ollama", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        print(result.stdout)
        sys.exit(1)
    
    model_name = sys.argv[1]
    test_model(model_name)