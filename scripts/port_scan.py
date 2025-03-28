#!/usr/bin/env python3
"""Script to scan for common Ollama ports on a specific host."""
import os
import sys
import socket
import time

# Configure host
HOST = os.environ.get("SCAN_HOST", "192.168.1.37")

# Common ports for Ollama and related services
COMMON_PORTS = [
    11434,  # Default Ollama API port
    8080,   # Common alternative web port
    8000,   # Common alternative web port
    3000,   # Common UI port
    7860,   # Gradio default port
    6000,   # Sometimes used for Ollama UI
    5000,   # Flask default port
    4000,   # Sometimes used for Ollama
    10000,  # Sometimes used for high ports
    9000,   # Sometimes used for high ports
]

# Custom port range scan
start_port = int(os.environ.get("START_PORT", "11430"))
end_port = int(os.environ.get("END_PORT", "11440"))

print(f"Scanning host {HOST} for open ports...")
print(f"Checking common ports: {COMMON_PORTS}")
print(f"Checking port range: {start_port}-{end_port}\n")

results = []

# First check the common ports
for port in COMMON_PORTS:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((HOST, port))
    if result == 0:
        print(f"✅ Port {port} is OPEN on {HOST}")
        results.append(port)
    sock.close()

# Then check the range of ports
for port in range(start_port, end_port + 1):
    if port not in COMMON_PORTS:  # Skip if already checked
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((HOST, port))
        if result == 0:
            print(f"✅ Port {port} is OPEN on {HOST}")
            results.append(port)
        sock.close()

print("\nScan completed.")
if results:
    print(f"Open ports on {HOST}: {results}")
    print("\nTry connecting to Ollama on one of these ports:")
    for port in results:
        print(f"export OLLAMA_HOST=http://{HOST}:{port} && python3 scripts/test_ollama.py")
else:
    print(f"No open ports found on {HOST}.")
    print("\nTroubleshooting steps:")
    print("1. Verify that Ollama is running on the specified host")
    print("2. Check firewall settings to ensure the port is accessible")
    print("3. Make sure Ollama is bound to all interfaces (not just localhost)")
    print("4. Try starting Ollama with: ollama serve --host 0.0.0.0")

# Write results to file
with open("PORT_SCAN_RESULTS.md", "w") as f:
    f.write(f"# Port Scan Results for {HOST}\n\n")
    f.write(f"- **Scan time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"- **Host:** {HOST}\n")
    f.write(f"- **Ports checked:** Common ports + range {start_port}-{end_port}\n\n")
    
    if results:
        f.write("## Open Ports Found\n\n")
        for port in results:
            f.write(f"- Port {port}\n")
        
        f.write("\n## Connection Commands\n\n")
        f.write("Try connecting to Ollama on one of these ports:\n\n")
        for port in results:
            f.write(f"```bash\nexport OLLAMA_HOST=http://{HOST}:{port} && python3 app/main.py\n```\n\n")
    else:
        f.write("No open ports found on the specified host.\n\n")
        
        f.write("## Troubleshooting\n\n")
        f.write("1. Verify that Ollama is running on the host with:\n")
        f.write("   ```bash\n   ssh user@host \"ps aux | grep ollama\"\n   ```\n\n")
        f.write("2. Check if Ollama is bound only to localhost:\n")
        f.write("   ```bash\n   ssh user@host \"sudo netstat -tulpn | grep ollama\"\n   ```\n\n")
        f.write("3. If Ollama is bound to 127.0.0.1 only, restart it with:\n")
        f.write("   ```bash\n   ssh user@host \"sudo systemctl stop ollama && sudo ollama serve --host 0.0.0.0\"\n   ```\n\n")
        f.write("4. Check firewall settings:\n")
        f.write("   ```bash\n   ssh user@host \"sudo ufw status\"\n   ```\n")

print(f"\nResults saved to PORT_SCAN_RESULTS.md")