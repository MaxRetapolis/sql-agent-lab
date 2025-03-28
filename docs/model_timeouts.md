# Model Timeout Configuration

This document describes how to configure timeouts for different operations in the SQL Agent application.

## Default Timeout Values

The application uses different timeout values for various model operations:

| Operation Type | Default Value | Description |
|----------------|---------------|-------------|
| `model_download` | 1200s (20min) | Time allowed for downloading/pulling models |
| `model_file_operations` | 600s (10min) | Time for other file operations with models |
| `connection_check` | 10s | Time for checking basic Ollama connectivity |
| `api_calls` | 30s | Time for Ollama API calls |
| `inference_first_token` | 60s | Time to wait for first token during inference |
| `inference_completion` | 300s (5min) | Time to wait for completing inference |
| `system_commands` | 10s | Time for system commands like checking Ollama installation |

## Configuring Timeouts

You can override the default timeouts using environment variables:

```bash
# Example: Set model download timeout to 30 minutes
export OLLAMA_TIMEOUT_MODEL_DOWNLOAD=1800

# Example: Set API calls timeout to 1 minute
export OLLAMA_TIMEOUT_API_CALLS=60

# Example: Set inference completion to 10 minutes
export OLLAMA_TIMEOUT_INFERENCE_COMPLETION=600
```

The environment variables follow the pattern `OLLAMA_TIMEOUT_<OPERATION_TYPE>` where `<OPERATION_TYPE>` is the uppercase version of the operation type.

## Suggestions for Different Environments

### Slower Hardware
For computers with limited resources:
- Increase `inference_first_token` to 120-180 seconds
- Increase `inference_completion` to 600 seconds (10 minutes)

### Faster Hardware
For high-performance servers:
- You can keep the default values or even reduce them

### Network Issues
If you experience network connectivity problems:
- Increase `connection_check` to 30 seconds
- Increase `api_calls` to 60 seconds

## Viewing Current Configuration

You can see the current timeout configuration by checking the `MODEL_TIMEOUTS` dictionary in the `src/sql_agent/utils/models/config.py` file or through the API:

```python
from sql_agent.utils.models.config import MODEL_TIMEOUTS

# Print all timeouts
print(MODEL_TIMEOUTS)

# Print specific timeout
from sql_agent.utils.models.config import get_timeout
print(get_timeout("inference_first_token"))
```