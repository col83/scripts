import requests
import socket
import time
import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== Default Configuration =====
DEFAULT_CONFIG = {
    "proxy_settings": {
        "proxy_list_url": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "backup_proxy_list": [
            "31.211.142.115:8192",
            "37.192.133.82:1080",
            "115.127.124.234:1080",
            "89.116.121.201:9051",
            "34.124.190.108:8080",
            "87.117.11.57:1080",
            "163.172.132.115:16379",
            "163.172.178.19:16379",
            "43.131.9.114:1777",
            "5.172.24.68:1080",
            "51.15.232.175:16379",
            "96.126.96.163:9090",
            "94.23.222.122:14822",
            "223.25.109.146:8199",
            "43.133.32.76:1777",
            "103.16.62.138:10888",
            "138.68.21.132:45793"
        ],
        "test_url": "http://httpbin.org/ip",
        "timeouts": {
            "total": 10,
            "port_check": 3,
            "request": 5
        },
        "max_threads": 4,
        "retry_count": 2,
        "delay_between_requests": 1
    },
    "geo_services": [
        {
            "name": "ip-api",
            "url": "http://ip-api.com/json/{ip}?fields=country,countryCode,city,isp,org,as,query",
            "parser_fields": {
                "country": "country",
                "code": "countryCode",
                "city": "city",
                "isp": "isp",
                "asn": "as"
            }
        }
    ]
}

def load_config(config_path=None):
    """Load configuration from file or use defaults"""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
                print(f"✅ Config loaded from {config_path}")
                return config
        except Exception as e:
            print(f"⚠ Error loading config: {e}, using defaults")
    
    print("ℹ  Using default configuration\n")
    return DEFAULT_CONFIG

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Check SOCKS5 proxies')
    parser.add_argument('--config', help='Path to config file')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--backup', action='store_true', help='Use backup proxy list')
    group.add_argument('--url', action='store_true', help='Use proxy list from URL')
    return parser.parse_args()

def load_proxy_list(config, use_backup=False, use_url=False):
    """Load proxy list according to arguments"""
    if use_backup:
        print("ℹ  Using backup proxy list (forced by --backup argument)\n")
        return config["proxy_settings"]["backup_proxy_list"]
    
    try:
        if not use_backup:
            url = config["proxy_settings"]["proxy_list_url"]
            print(f"⌛ Trying to load proxy list from {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                proxies = [
                    line.strip() for line in response.text.splitlines()
                    if line.strip() and ':' in line and not line.startswith('#')
                    and len(line.split(':')) == 2 and line.split(':')[1].isdigit()
                ]
                if proxies:
                    print(f"✅ Successfully loaded {len(proxies)} valid proxies")
                    return proxies
    except Exception as e:
        print(f"⚠ Failed to load proxy list: {e}")
    
    if not use_url:
        print("ℹ Using backup proxy list (fallback)")
        return config["proxy_settings"]["backup_proxy_list"]
    
    print("⚠ Failed to load proxies and --url was requested. Exiting.")
    exit(1)

def get_geo_info(ip, config):
    """Get geo information for IP"""
    for service in config["geo_services"]:
        for attempt in range(config["proxy_settings"]["retry_count"]):
            try:
                time.sleep(config["proxy_settings"]["delay_between_requests"])
                response = requests.get(
                    service["url"].format(ip=ip),
                    timeout=config["proxy_settings"]["timeouts"]["request"],
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'service': service['name'],
                        'country': data.get(service['parser_fields']['country'], 'Unknown'),
                        'code': data.get(service['parser_fields']['code'], 'XX'),
                        'city': data.get(service['parser_fields']['city'], 'Unknown'),
                        'isp': data.get(service['parser_fields']['isp'], 'Unknown'),
                        'asn': data.get(service['parser_fields']['asn'], 'Unknown')
                    }
            except Exception as e:
                print(f"⚠ Error {service['name']} for {ip}: {e}")
                time.sleep(1)
    
    return {
        'service': 'failed',
        'country': 'Unknown',
        'code': 'XX',
        'city': 'Unknown',
        'isp': 'Unknown',
        'asn': 'Unknown'
    }

def check_proxy(proxy, config):
    """Check proxy with configurable timeouts"""
    start_time = time.time()
    
    try:
        ip, port = proxy.split(':')
        port = int(port)
    except:
        return None
    
    try:
        # Port check
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(config["proxy_settings"]["timeouts"]["port_check"])
            if s.connect_ex((ip, port)) != 0:
                return None
        
        # HTTP check
        proxies = {"http": f"socks5://{proxy}", "https": f"socks5://{proxy}"}
        try:
            response = requests.get(
                config["proxy_settings"]["test_url"],
                proxies=proxies,
                timeout=config["proxy_settings"]["timeouts"]["request"]
            )
            if response.status_code != 200:
                return None
        except:
            return None
        
        # Total timeout check
        if (time.time() - start_time) > config["proxy_settings"]["timeouts"]["total"]:
            return None
            
        # Get geo info
        geo_info = get_geo_info(ip, config)
        
        return {
            'proxy': proxy,
            'ip': ip,
            **geo_info
        }
    except Exception:
        return None

def main():
    print("\n🔍 Starting proxy checking...\n")
    
    args = parse_arguments()
    config = load_config(args.config)
    
    proxies = load_proxy_list(
        config,
        use_backup=args.backup,
        use_url=args.url
    )
    
    results = []
    with ThreadPoolExecutor(max_workers=config["proxy_settings"]["max_threads"]) as executor:
        future_to_proxy = {
            executor.submit(check_proxy, proxy, config): proxy 
            for proxy in proxies
        }
        
        for future in as_completed(future_to_proxy):
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"✓ Checked {result['proxy']} ({result['country']})")
            except Exception as e:
                print(f"⚠ Error checking proxy: {e}")
    
    # Print results
    print("\n🎯 Workers proxy:\n")
    # Оптимальные ширины столбцов
    print("{:<22} {:<6} {:<15} {:<20} {:<35}".format(
        "Proxy", "Code", "Country", "City", "Provider"
    ))
    print("-" * 98)  # Общая ширина соответствует сумме столбцов
    
    for info in results:
        print("{:<22} {:<6} {:<15} {:<20} {:<35}".format(
            info['proxy'],
            info['code'],
            info['country'],
            info['city'][:18] + '..' if len(info['city']) > 18 else info['city'],
            info['isp'][:33] + '..' if len(info['isp']) > 33 else info['isp']
        ))
    
    print(f"\n📊 Result: {len(results)} workers out of {len(proxies)}")

if __name__ == "__main__":
    main()