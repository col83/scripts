import requests
import socket
import time
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_default_config_path():
    """Get default config path in the same directory as script"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "config.json")

def validate_config(config):
    """Validate the configuration structure"""
    required_keys = {
        "proxy_settings": ["proxy_list_url", "backup_proxy_list", "test_url", 
                          "timeouts", "max_threads", "retry_count", 
                          "delay_between_requests"],
        "geo_services": [{
            "name": str,
            "url": str,
            "parser_fields": {
                "country": str,
                "code": str,
                "city": str,
                "isp": str
            }
        }]
    }
    
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    
    for main_key, sub_keys in required_keys.items():
        if main_key not in config:
            raise ValueError(f"Missing required section: {main_key}")
        
        if main_key == "proxy_settings":
            for key in sub_keys:
                if key not in config["proxy_settings"]:
                    raise ValueError(f"Missing proxy_settings key: {key}")
                    
            # Validate timeouts
            timeout_keys = ["total", "port_check", "request"]
            for key in timeout_keys:
                if key not in config["proxy_settings"]["timeouts"]:
                    raise ValueError(f"Missing timeout key: {key}")
                    
        elif main_key == "geo_services":
            if not isinstance(config["geo_services"], list) or len(config["geo_services"]) == 0:
                raise ValueError("geo_services must be a non-empty list")
            
            for service in config["geo_services"]:
                for key in sub_keys[0].keys():
                    if key not in service:
                        raise ValueError(f"Missing geo_service key: {key}")

def load_config(config_path=None):
    """Load and validate configuration from file"""
    if config_path is None:
        config_path = get_default_config_path()
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            validate_config(config)
            print(f"✅ Config loaded from {config_path}\n")
            return config
    except Exception as e:
        print(f"⚠ Error loading config: {e}")
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Check SOCKS5 proxies')
    parser.add_argument('--config', help='Path to config file (default: config.json in script directory)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--backup', action='store_true', help='Use backup proxy list')
    group.add_argument('--url', action='store_true', help='Use proxy list from URL')
    return parser.parse_args()

def load_proxy_list(config, use_backup=False, use_url=False):
    """Load proxy list according to arguments"""
    if use_backup:
        print("ℹ Using backup proxy list (forced by --backup argument)")
        return config["proxy_settings"]["backup_proxy_list"]
    
    try:
        if not use_backup:
            url = config["proxy_settings"]["proxy_list_url"]
            print(f"⌛ Trying to load proxy list from {url}\n")
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
        print("ℹ  Using backup proxy list (fallback)")
        return config["proxy_settings"]["backup_proxy_list"]
    
    print("⚠ Failed to load proxies and --url was requested. Exiting.")
    sys.exit(1)

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
                        'country': data.get(service['parser_fields']['country']), 
                        'code': data.get(service['parser_fields']['code']),
                        'city': data.get(service['parser_fields']['city']),
                        'isp': data.get(service['parser_fields']['isp'])
                    }
            except Exception as e:
                print(f"⚠ Error {service['name']} for {ip}: {e}")
                time.sleep(1)
    
    return {
        'country': 'Unknown',
        'code': 'XX',
        'city': 'Unknown',
        'isp': 'Unknown'
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
    print("{:<22} {:<6} {:<15} {:<20} {:<35}".format(
        "Proxy", "Code", "Country", "City", "Provider"
    ))
    print("-" * 98)
    
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