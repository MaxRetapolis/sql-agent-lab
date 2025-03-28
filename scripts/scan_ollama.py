#!/usr/bin/env python3
"""Script to scan network for Ollama servers."""
import os
import sys
import requests
import json
import time
import concurrent.futures
import socket

def test_host(ip, port=11434, timeout=2):
    """Test if we can connect to the given host and port."""
    try:
        # First check if we can connect to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result != 0:
            return {
                "ip": ip,
                "port": port,
                "status": "closed",
                "error": f"Port {port} is closed"
            }
        
        # If port is open, try to connect to Ollama API
        url = f"http://{ip}:{port}/api/version"
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            version = response.json().get("version", "unknown")
            return {
                "ip": ip,
                "port": port,
                "status": "ollama_found",
                "version": version
            }
        else:
            return {
                "ip": ip,
                "port": port,
                "status": "not_ollama",
                "error": f"HTTP {response.status_code}"
            }
    except requests.RequestException as e:
        return {
            "ip": ip,
            "port": port,
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        return {
            "ip": ip,
            "port": port,
            "status": "error",
            "error": str(e)
        }

def scan_network(base_ip, start=1, end=254, port=11434, timeout=2, max_workers=50):
    """Scan the network for Ollama servers."""
    results = []
    base_parts = base_ip.split('.')
    if len(base_parts) != 4:
        print(f"Invalid base IP: {base_ip}")
        return []
    
    # Create the base for the IP
    base = '.'.join(base_parts[:3]) + '.'
    
    print(f"Scanning {base}[{start}-{end}]:{port} for Ollama servers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {
            executor.submit(test_host, f"{base}{i}", port, timeout): f"{base}{i}" 
            for i in range(start, end + 1)
        }
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_ip), 1):
            ip = future_to_ip[future]
            try:
                result = future.result()
                # Print progress
                sys.stdout.write(f"\rScanning: {i}/{end-start+1} IPs checked...")
                sys.stdout.flush()
                
                if result["status"] == "ollama_found":
                    print(f"\n✅ Found Ollama v{result['version']} at {ip}:{port}")
                    results.append(result)
            except Exception as e:
                print(f"\n❌ Error processing {ip}: {e}")
    
    print(f"\nScan completed. Found {len(results)} Ollama servers.")
    return results

def main():
    """Main function."""
    # Get base IP from environment or use default
    base_ip = os.environ.get("NETWORK_IP", "192.168.1.1")
    scan_start = int(os.environ.get("SCAN_START", "1"))
    scan_end = int(os.environ.get("SCAN_END", "254"))
    
    results = scan_network(base_ip, scan_start, scan_end)
    
    # Save results to file
    with open("OLLAMA_SCAN_RESULTS.md", "w") as f:
        f.write(f"# Ollama Network Scan Results\n\n")
        f.write(f"- **Scan time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Network scanned:** {base_ip.rsplit('.', 1)[0]}.0/24\n")
        f.write(f"- **IP range:** {scan_start}-{scan_end}\n")
        f.write(f"- **Servers found:** {len(results)}\n\n")
        
        if results:
            f.write("## Ollama Servers Found\n\n")
            for result in results:
                f.write(f"### {result['ip']}:11434\n")
                f.write(f"- **Version:** {result.get('version', 'unknown')}\n")
                f.write(f"- **Status:** {result['status']}\n")
                f.write(f"- **Connection string:** `OLLAMA_HOST=http://{result['ip']}:{result['port']}`\n\n")
                f.write(f"To use this server, run:\n")
                f.write(f"```bash\nexport OLLAMA_HOST=http://{result['ip']}:{result['port']}\npython app/main.py\n```\n\n")
        else:
            f.write("\nNo Ollama servers found in the specified network range.\n\n")
            f.write("Troubleshooting steps:\n")
            f.write("1. Verify Ollama is running on at least one machine in your network\n")
            f.write("2. Check that the machine running Ollama has port 11434 open\n")
            f.write("3. Ensure there are no firewall rules blocking access\n")
            f.write("4. Try running `curl http://<ollama-ip>:11434/api/version` from this machine\n")
    
    # Save JSON results
    with open("ollama_scan_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to OLLAMA_SCAN_RESULTS.md and ollama_scan_results.json")
    
    return 0 if results else 1

if __name__ == "__main__":
    sys.exit(main())