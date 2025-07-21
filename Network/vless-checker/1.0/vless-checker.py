import requests
import time
import json
import os
import socket
import re
import base64
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def is_ip_address(addr):
    try:
        socket.inet_aton(addr)
        return True
    except socket.error:
        return False

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
            required = ['max_threads', 'timeouts', 'ignored_ports', 'max_displayed_ips']
            for param in required:
                if param not in config.get('settings', {}):
                    print(f"❌ Config error: Missing required parameter '{param}'")
                    sys.exit(1)
            return config
    except Exception as e:
        print(f"❌ Config error: {e}")
        sys.exit(1)

def load_proxy_list(filepath=None, url=None):
    try:
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        elif url:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                try:
                    decoded = base64.b64decode(response.content).decode('utf-8')
                    return [line.strip() for line in decoded.splitlines() if line.strip()]
                except:
                    return [line.strip() for line in response.text.splitlines() if line.strip()]
            print(f"❌ Download failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"\n❌ Load error: {e}")
    sys.exit(1)

def parse_vless_uri(uri, ignored_ports):
    try:
        uri = uri.strip()
        if not uri.startswith('vless://'):
            return None

        server_part = uri.split('@', 1)[1].split('?', 1)[0]
        server, port = server_part.rsplit(':', 1)

        if not is_ip_address(server) or int(port) in ignored_ports:
            return None

        return {
            'server': server,
            'port': port,
            'uri': uri[:100] + '...' if len(uri) > 100 else uri
        }
    except Exception:
        return None

def check_connection(proxy, timeout):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((proxy['server'], int(proxy['port'])))
            return True
    except Exception:
        return False

def check_tcp_response(ip, port, timeout=2):
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, int(port)))
            latency = int((time.time() - start_time) * 1000)  # Convert to milliseconds
            return latency
    except:
        return None

def main():
    print("\n⚡ VLESS IP Checker (TCP Only) ⚡\n")
    
    config = load_config()
    settings = config['settings']
    
    max_threads = settings['max_threads']
    port_check_timeout = settings['timeouts']['port_check']
    tcp_check_timeout = settings['timeouts']['tcp_check']
    ignored_ports = settings['ignored_ports']
    max_displayed = settings['max_displayed_ips']
    debug_mode = settings.get('debug_mode', False)

    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        if len(sys.argv) < 3:
            print("❌ Ошибка: не указан файл для загрузки (используйте --file /путь/к/файлу)")
            sys.exit(1)
        filepath = sys.argv[2]
        print(f"⌛ Loading from file: {filepath}")
        proxy_lines = load_proxy_list(filepath=filepath)
    else:
        proxy_url = settings.get('proxy_list_url')
        if not proxy_url:
            print("❌ Config error: Missing 'proxy_list_url' in config")
            sys.exit(1)
        print(f"⌛ Downloading from {proxy_url}")
        proxy_lines = load_proxy_list(url=proxy_url)
    
    print(f"\n✅ Loaded {len(proxy_lines)} proxies")
    print(f"\n⚙  Filtering IP addresses (excluding ports: {', '.join(map(str, ignored_ports))})...")
    
    filtered_proxies = []
    for line in proxy_lines:
        proxy = parse_vless_uri(line, ignored_ports)
        if proxy:
            filtered_proxies.append(proxy)
    
    if not filtered_proxies:
        print("\n❌ No valid IP addresses found after filtering!")
        sys.exit(1)

    print(f"\n⚡ Checking {len(filtered_proxies)} filtered IP addresses...\n")
    working_ips = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(check_connection, p, port_check_timeout): p 
                  for p in filtered_proxies}
        for i, future in enumerate(as_completed(futures), 1):
            if future.result():
                working_ips.append(futures[future])
            if i % 50 == 0:
                print(f"ℹ️ Checked {i}/{len(filtered_proxies)}...", end='\r')

    print()
    print(f"\n📡 Measuring TCP latency for {len(working_ips)} IPs...\n")
    verified_ips = []
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {executor.submit(check_tcp_response, p['server'], p['port'], 
                  tcp_check_timeout): p for p in working_ips}
        for i, future in enumerate(as_completed(futures), 1):
            latency = future.result()
            if latency is not None:
                proxy = futures[future]
                proxy['latency'] = latency
                verified_ips.append(proxy)
            sys.stdout.write(f"\r📡 Measured {i}/{len(working_ips)}...")
            sys.stdout.flush()
    print()

    print(f"\n✅ Results: {len(verified_ips)} working IPs")
    if verified_ips:
        display_count = len(verified_ips)
        if max_displayed > 0:
            display_count = min(max_displayed, len(verified_ips))
        
        print(f"\n🏆 Working IPs (showing {display_count} of {len(verified_ips)}):\n")
        for proxy in sorted(verified_ips[:display_count], key=lambda x: x['latency']):
            print(f"- {proxy['server']}:{proxy['port']} ({proxy['latency']}ms)")
        
        if max_displayed > 0 and len(verified_ips) > max_displayed:
            print(f"\nℹ️ {len(verified_ips) - max_displayed} more IPs available (adjust max_displayed_ips in config.json)")

if __name__ == "__main__":
    main()