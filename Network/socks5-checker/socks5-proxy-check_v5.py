import requests
import socket
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== settings =====
# Built-in proxy backup list
BACKUP_PROXY_LIST = """
31.211.142.115:8192
37.192.133.82:1080
115.127.124.234:1080
89.116.121.201:9051
34.124.190.108:8080
87.117.11.57:1080
163.172.132.115:16379
163.172.178.19:16379
43.131.9.114:1777
5.172.24.68:1080
51.15.232.175:16379
96.126.96.163:9090
94.23.222.122:14822
223.25.109.146:8199
43.133.32.76:1777
103.16.62.138:10888
138.68.21.132:45793
"""

# URL to download proxy list
PROXY_LIST_URL = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt"

TEST_URL = "http://httpbin.org/ip"
TOTAL_TIMEOUT = 10  # Total timeout for checking one proxy (seconds)
PORT_CHECK_TIMEOUT = 3  # Port check timeout
REQUEST_TIMEOUT = 5  # HTTP request timeout
MAX_THREADS = 4  # Number of threads
RETRY_COUNT = 2  # Number of attempts for geoservices
DELAY_BETWEEN_REQUESTS = 1  # Delay between requests (seconds)

# Geolocation services
GEO_SERVICES = [
    {
        'name': 'ip-api',
        'url': 'http://ip-api.com/json/{ip}?fields=country,countryCode,city,isp,org,as,query',
        'parser': lambda data: {
            'country': data.get('country', 'Unknown'),
            'code': data.get('countryCode', 'XX'),
            'city': data.get('city', 'Unknown'),
            'isp': data.get('isp', 'Unknown'),
            'asn': data.get('as', '').split()[0] if data.get('as') else 'Unknown'
        }
    },
    {
        'name': 'ipwhois',
        'url': 'https://ipwhois.app/json/{ip}',
        'parser': lambda data: {
            'country': data.get('country', 'Unknown'),
            'code': data.get('country_code', 'XX'),
            'city': data.get('city', 'Unknown'),
            'isp': data.get('isp', 'Unknown'),
            'asn': data.get('asn', 'Unknown')
        }
    }
]

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Check SOCKS5 proxies')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--backup', action='store_true', help='Use backup proxy list')
    group.add_argument('--url', action='store_true', help='Use proxy list from URL')
    
    args = parser.parse_args()
    return args

def load_proxy_list(url, backup_list, use_backup=False, use_url=False):
    """Loads a list of proxies from a URL or uses a fallback list"""
    # If --backup was specified
    if use_backup:
        print("ℹ  Using backup proxy list (forced by --backup argument)\n")
        return [p.strip() for p in backup_list.split("\n") if p.strip() and ':' in p]
    
    # If --url was specified or no arguments were provided (default behavior)
    try:
        if not use_backup:
            print(f"⌛ Trying to load proxy list from {url}\n")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Filter only lines in IP:PORT format
                proxies = []
                for line in response.text.splitlines():
                    line = line.strip()
                    if line and ':' in line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 2 and parts[1].isdigit():
                            proxies.append(line)
                
                if proxies:
                    print(f"✅ Successfully loaded {len(proxies)} valid proxies from URL\n")
                    return proxies
    except Exception as e:
        print(f"⚠ Failed to load proxy list from URL: {str(e)}")
    
    # Fallback to backup list if URL loading failed and --url was not explicitly requested
    if not use_url:
        print("ℹ  Using backup proxy list (fallback)\n")
        return [p.strip() for p in backup_list.split("\n") if p.strip() and ':' in p]
    else:
        print("⚠ Failed to load proxies from URL and --url was explicitly requested. Exiting.")
        exit(1)

def get_geo_info(ip):
    """Gets geo-information for IP with service rotation"""
    for service in GEO_SERVICES:
        for attempt in range(RETRY_COUNT):
            try:
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                response = requests.get(
                    service['url'].format(ip=ip),
                    timeout=REQUEST_TIMEOUT,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'service': service['name'],
                        **service['parser'](data)
                    }
                
            except Exception as e:
                print(f"⚠ Error {service['name']} для {ip} (attempt {attempt+1}): {str(e)}")
                time.sleep(1)
    
    return {
        'service': 'failed',
        'country': 'Unknown',
        'code': 'XX',
        'city': 'Unknown',
        'isp': 'Unknown',
        'asn': 'Unknown'
    }

def check_proxy(proxy):
    """Checks proxies with a common time limit"""
    start_time = time.time()
    
    try:
        ip, port = proxy.split(':')
        port = int(port)  # Check that the port is a number
    except:
        return None
    
    try:
        # 1. PORT check
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(PORT_CHECK_TIMEOUT)
            if s.connect_ex((ip, port)) != 0:
                return None
        
        # 2. HTTP check
        proxies = {"http": f"socks5://{proxy}", "https": f"socks5://{proxy}"}
        try:
            response = requests.get(TEST_URL, proxies=proxies, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                return None
        except:
            return None
        
        # 3. Checking the total time
        if (time.time() - start_time) > TOTAL_TIMEOUT:
            return None
            
        # 4. Getting geolocation information
        geo_info = get_geo_info(ip)
        
        return {
            'proxy': proxy,
            'ip': ip,
            **geo_info
        }
            
    except Exception:
        return None

# ===== main =====
if __name__ == "__main__":
    print("\n🔍 Starting proxy checking...\n")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load proxy list according to arguments
    proxies = load_proxy_list(
        PROXY_LIST_URL, 
        BACKUP_PROXY_LIST,
        use_backup=args.backup,
        use_url=args.url
    )
    
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_proxy = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
        
        for future in as_completed(future_to_proxy):
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"✓ Checked {result['proxy']} ({result['country']})")
            except Exception as e:
                print(f"⚠ Error checking proxy: {str(e)}")
    
    # print results
    print("\n🎯 Workers proxy:\n")
    print("{:<20} {:<8} {:<15} {:<20} {:<25} {:<10} {:<10}".format(
        "Proxy", "Code", "Country", "City", "Provider", "ASN", "Service"
    ))
    print("-" * 111)
    
    for info in results:
        print("{:<20} {:<8} {:<15} {:<20} {:<25} {:<10} {:<10}".format(
            info['proxy'],
            info['code'],
            info['country'],
            info['city'][:18] + '...' if len(info['city']) > 18 else info['city'],
            info['isp'][:22] + '...' if len(info['isp']) > 22 else info['isp'],
            info['asn'],
            info['service']
        ))
    
    print(f"\n📊 Result: {len(results)} workers out of {len(proxies)}")