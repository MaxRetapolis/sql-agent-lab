#!/usr/bin/env python3
"""Script to test connectivity to Ollama server."""
import os
import sys
import requests
import json
import time

# Configure Ollama host
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.1.37:11434")
print(f"Testing connection to Ollama at {OLLAMA_HOST}...")

# Initialize result
result = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "host": OLLAMA_HOST,
    "status": "unavailable",
    "version": "unknown",
    "error": None
}

try:
    # Test basic connectivity
    response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=5)
    if response.status_code == 200:
        result["status"] = "available"
        result["version"] = response.json().get("version", "unknown")
        print(f"✅ Successfully connected to Ollama v{result['version']}")
        
        # Try to list models
        try:
            models_response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if models_response.status_code == 200:
                models = models_response.json().get("models", [])
                result["model_count"] = len(models)
                result["models"] = [model.get("name") for model in models]
                print(f"Found {len(models)} models on the server:")
                for model in models:
                    print(f"  - {model.get('name')}")
            else:
                print(f"⚠️ Got response code {models_response.status_code} when listing models")
                result["error"] = f"Error listing models: HTTP {models_response.status_code}"
        except Exception as e:
            print(f"⚠️ Error listing models: {e}")
            result["error"] = f"Error listing models: {str(e)}"
    else:
        result["status"] = "error"
        result["error"] = f"HTTP status: {response.status_code}"
        print(f"❌ Failed to connect to Ollama: HTTP {response.status_code}")
except requests.RequestException as e:
    result["status"] = "connection_error"
    result["error"] = str(e)
    print(f"❌ Connection error: {e}")

# Save results to file
with open("OLLAMA_TEST_RESULTS.md", "w") as f:
    f.write(f"# Ollama Connection Test\n\n")
    f.write(f"- **Test time:** {result['timestamp']}\n")
    f.write(f"- **Host:** {result['host']}\n")
    f.write(f"- **Status:** {'Connected' if result['status'] == 'available' else 'Failed'}\n")
    
    if result["status"] == "available":
        f.write(f"- **Version:** {result['version']}\n")
        if "model_count" in result:
            f.write(f"- **Models available:** {result['model_count']}\n")
            if "models" in result and result["models"]:
                f.write("\n### Available Models:\n")
                for model in result["models"]:
                    f.write(f"- {model}\n")
        f.write("\nConnection successful! The application should work correctly.")
    else:
        f.write(f"- **Error:** {result.get('error', 'Unknown error')}\n\n")
        f.write("Troubleshooting steps:\n")
        f.write("1. Verify Ollama is running on the specified host\n")
        f.write("2. Check network connectivity to the host\n")
        f.write("3. Ensure port 11434 is open on the host\n")
        f.write("4. Try running this command on the host: `curl http://localhost:11434/api/version`\n")

# Save JSON results
with open("ollama_test_results.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"\nResults saved to OLLAMA_TEST_RESULTS.md and ollama_test_results.json")

# Set exit code based on connection status
sys.exit(0 if result["status"] == "available" else 1)