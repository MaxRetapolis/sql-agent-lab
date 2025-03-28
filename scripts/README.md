# SQL Agent Utility Scripts

This directory contains utility scripts for the SQL Agent application.

## Ollama Connectivity Scripts

### test_ollama.py

Tests connectivity to a specific Ollama server.

```bash
# Test default server (from OLLAMA_HOST or 192.168.1.37)
python3 test_ollama.py

# Test specific server
OLLAMA_HOST=http://192.168.1.100:11434 python3 test_ollama.py
```

Output:
- Console log of test results
- `OLLAMA_TEST_RESULTS.md` - Human-readable report
- `ollama_test_results.json` - Machine-readable JSON

### scan_ollama.py

Scans your local network for Ollama servers.

```bash
# Scan entire subnet (192.168.1.1-254)
python3 scan_ollama.py

# Scan specific range
SCAN_START=30 SCAN_END=50 python3 scan_ollama.py

# Scan different subnet
NETWORK_IP=10.0.0.1 python3 scan_ollama.py
```

Output:
- Console log of scan progress and results
- `OLLAMA_SCAN_RESULTS.md` - Human-readable report with connection instructions
- `ollama_scan_results.json` - Machine-readable JSON

## Using the Results

If scan_ollama.py finds servers, you can use the connection string it provides:

```bash
export OLLAMA_HOST=http://192.168.1.100:11434
python3 app/main.py
```

Or use the `/set_ollama_host` command in the application:

```
/set_ollama_host http://192.168.1.100:11434
```