#!/usr/bin/env python3
"""Script to test connectivity to Ollama server with extended diagnostics."""
import os
import sys
import subprocess
import socket
import requests
import json
import time

# Configure Ollama host
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://192.168.1.37:11434")
print(f"Testing connection to Ollama at {OLLAMA_HOST}...")

# Perform basic network diagnostics
host = OLLAMA_HOST.replace("http://", "").replace("https://", "").split(":")[0]
port = 11434

print(f"\n==== Basic Network Diagnostics for {host} ====")

# Test if the host is reachable with ping
try:
    print(f"\nAttempting to ping {host}...")
    ping_result = subprocess.run(
        ["ping", "-c", "3", "-W", "2", host], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True,
        timeout=20
    )
    print(ping_result.stdout)
    if ping_result.returncode != 0:
        print(f"❌ Unable to ping {host}")
    else:
        print(f"✅ Host {host} responds to ping")
except Exception as e:
    print(f"❌ Error running ping: {e}")

# Try a socket connection to the port
print(f"\nAttempting to connect to port {port} on {host}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(20)  # Longer timeout
result = sock.connect_ex((host, port))
if result == 0:
    print(f"✅ Port {port} is open on {host}")
else:
    print(f"❌ Port {port} is closed or blocked on {host}")
sock.close()

# Initialize result
result = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "host": OLLAMA_HOST,
    "status": "unavailable",
    "version": "unknown",
    "error": None,
    "ping_success": ping_result.returncode == 0 if 'ping_result' in locals() else False,
    "port_open": result == 0
}

print(f"\n==== Attempting API Connection with Extended Timeout ====")
try:
    # Test basic connectivity with longer timeout
    print(f"Connecting to {OLLAMA_HOST}/api/version with 30-second timeout...")
    response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=30)
    if response.status_code == 200:
        result["status"] = "available"
        result["version"] = response.json().get("version", "unknown")
        print(f"✅ Successfully connected to Ollama v{result['version']}")
    else:
        result["status"] = "error"
        result["error"] = f"HTTP status: {response.status_code}"
        print(f"❌ Failed to connect to Ollama: HTTP {response.status_code}")
except requests.RequestException as e:
    result["status"] = "connection_error"
    result["error"] = str(e)
    print(f"❌ Connection error: {e}")

# Save detailed results to file
with open("OLLAMA_EXTENDED_TEST_RESULTS.md", "w") as f:
    f.write(f"# Ollama Extended Connection Test\n\n")
    f.write(f"- **Test time:** {result['timestamp']}\n")
    f.write(f"- **Host:** {result['host']}\n")
    f.write(f"- **Status:** {'Connected' if result['status'] == 'available' else 'Failed'}\n")
    f.write(f"- **Ping status:** {'Success' if result['ping_success'] else 'Failed'}\n")
    f.write(f"- **Port {port} status:** {'Open' if result['port_open'] else 'Closed/Blocked'}\n")
    
    if result["status"] == "available":
        f.write(f"- **Ollama version:** {result['version']}\n\n")
        f.write("Connection successful! The application should work correctly.")
    else:
        f.write(f"- **Error:** {result.get('error', 'Unknown error')}\n\n")
        f.write("## Diagnostics\n\n")
        
        if not result['ping_success']:
            f.write("- ❌ Host does not respond to ping\n")
            f.write("  - This could indicate the host is down or not reachable\n")
            f.write("  - Check if the IP address is correct\n")
            f.write("  - Check network connectivity between machines\n\n")
        else:
            f.write("- ✅ Host responds to ping\n\n")
        
        if not result['port_open']:
            f.write("- ❌ Port 11434 is closed or blocked\n")
            f.write("  - Check if Ollama is running on the host\n")
            f.write("  - Check if a firewall is blocking the port\n")
            f.write("  - Try running this command on the host: `curl http://localhost:11434/api/version`\n\n")
        else:
            f.write("- ✅ Port 11434 is open\n\n")
        
        f.write("## Troubleshooting steps\n\n")
        f.write("1. Verify Ollama is running on the host with:\n")
        f.write("   ```bash\n   ps aux | grep ollama\n   ```\n\n")
        f.write("2. Check Ollama's logs on the host with:\n")
        f.write("   ```bash\n   journalctl -u ollama\n   ```\n\n")
        f.write("3. Verify local connectivity on the host with:\n")
        f.write("   ```bash\n   curl http://localhost:11434/api/version\n   ```\n\n")
        f.write("4. Check firewall settings on the host with:\n")
        f.write("   ```bash\n   sudo ufw status\n   # or\n   sudo iptables -L\n   ```\n\n")
        f.write("5. If using Docker, ensure port 11434 is mapped correctly:\n")
        f.write("   ```bash\n   docker ps | grep ollama\n   ```\n")
        

# Save JSON results
with open("ollama_extended_test_results.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"\nResults saved to OLLAMA_EXTENDED_TEST_RESULTS.md and ollama_extended_test_results.json")

# Set exit code based on connection status
sys.exit(0 if result["status"] == "available" else 1)