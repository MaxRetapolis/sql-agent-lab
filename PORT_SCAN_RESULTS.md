# Port Scan Results for 192.168.1.37

- **Scan time:** 2025-03-27 22:28:18
- **Host:** 192.168.1.37
- **Ports checked:** Common ports + range 11430-11440

No open ports found on the specified host.

## Troubleshooting

1. Verify that Ollama is running on the host with:
   ```bash
   ssh user@host "ps aux | grep ollama"
   ```

2. Check if Ollama is bound only to localhost:
   ```bash
   ssh user@host "sudo netstat -tulpn | grep ollama"
   ```

3. If Ollama is bound to 127.0.0.1 only, restart it with:
   ```bash
   ssh user@host "sudo systemctl stop ollama && sudo ollama serve --host 0.0.0.0"
   ```

4. Check firewall settings:
   ```bash
   ssh user@host "sudo ufw status"
   ```
