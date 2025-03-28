# Ollama Network Scan Results

- **Scan time:** 2025-03-27 22:23:37
- **Network scanned:** 192.168.1.0/24
- **IP range:** 30-50
- **Servers found:** 0


No Ollama servers found in the specified network range.

Troubleshooting steps:
1. Verify Ollama is running on at least one machine in your network
2. Check that the machine running Ollama has port 11434 open
3. Ensure there are no firewall rules blocking access
4. Try running `curl http://<ollama-ip>:11434/api/version` from this machine
