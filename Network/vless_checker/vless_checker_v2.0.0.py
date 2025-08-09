import re
import socket
from urllib.parse import urlparse, parse_qs
import requests
import sys
import os
from datetime import datetime
import urwid
import threading
import queue
import base64
import json
import time

# Константы
FLAGS = ["🇩🇪", "🇳🇱", "🇵🇱", "🇸🇪"]
FORBIDDEN_PROTOCOLS = ['http', 'socks', 'socks4', 'socks5']
FORBIDDEN_TYPES = ['grpc', 'http', 'h2', 'xhttp', 'httpupgrade']
FORBIDDEN_PORTS = {80, 8080, 8880}
CONFIG_URL = "https://raw.githubusercontent.com/wuqb2i4f/xray-config-toolkit/refs/heads/main/output/base64/mix-protocol-vl"

class VlessCheckerTUI:
    def __init__(self):
        self.loop = None
        self.log_queue = queue.Queue()
        self.progress = 0
        self.total = 0
        self.alive_configs = []
        self.main_widget = None
        self.stop_event = threading.Event()
        self.setup_ui()
        
    def setup_ui(self):
        # Элементы интерфейса
        self.header = urwid.Text(('header', "VLESS Reality TLS Checker"), align='center')
        self.log_list = urwid.SimpleListWalker([])
        self.log_box = urwid.ListBox(self.log_list)
        self.progress_bar = urwid.Text("Progress: 0/0")
        self.status_text = urwid.Text("Ready to start")
        
        # Компоновка интерфейса
        self.main_widget = urwid.Frame(
            header=urwid.Pile([
                ('fixed', 1, urwid.Filler(self.header)),
                urwid.Divider(),
                ('fixed', 1, urwid.Filler(urwid.Text("Logs:"))),
            ]),
            body=self.log_box,
            footer=urwid.Pile([
                ('fixed', 1, urwid.Filler(self.status_text)),
                ('fixed', 1, urwid.Filler(self.progress_bar)),
                ('fixed', 1, urwid.Filler(urwid.Text("Press [Q] to quit | [R] to run check | [V] to view results | [Ctrl+C] to stop"))),
            ])
        )
        
    def add_log(self, message, level='info'):
        """Добавить сообщение в лог"""
        color_map = {
            'info': 'log_info',
            'success': 'log_success',
            'error': 'log_error',
            'warning': 'log_warning'
        }
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        self.log_queue.put((formatted_msg, color_map.get(level, 'log_info')))
        
    def update_log_display(self):
        """Обновить отображение логов из очереди"""
        while not self.log_queue.empty():
            msg, color = self.log_queue.get()
            self.log_list.append(urwid.Text((color, msg)))
            self.log_box.set_focus(len(self.log_list) - 1, 'above')
            
    def set_progress(self, current, total):
        """Обновить прогресс-бар"""
        self.progress = current
        self.total = total
        progress_percent = (current / total) * 100 if total > 0 else 0
        progress_text = f"Progress: [{current}/{total}] {progress_percent:.1f}%"
        self.progress_bar.set_text(progress_text)
        self.status_text.set_text(f"Processing: {current}/{total}")
        
    def run_in_thread(self, target, *args):
        """Запустить функцию в отдельном потоке"""
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        thread.start()
        
    def download_config_list(self, url):
        """Загрузить список конфигураций"""
        try:
            self.add_log(f"Downloading configurations from {url}...")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            content = ""
            for chunk in response.iter_content(chunk_size=8192):
                if self.stop_event.is_set():
                    self.add_log("Download interrupted by user", 'warning')
                    return []
                if chunk:  # filter out keep-alive new chunks
                    content += chunk.decode('utf-8')
                    
            lines = content.splitlines()
            self.add_log(f"Downloaded {len(lines)} lines", 'success')
            return lines
        except requests.exceptions.RequestException as e:
            self.add_log(f"Network error downloading list: {e}", 'error')
            return []
        except Exception as e:
            self.add_log(f"Error downloading list: {e}", 'error')
            return []
            
    def is_ip_address(self, host):
        """Проверить, является ли хост IP-адресом"""
        return re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host) is not None
        
    def has_reality_settings(self, config_str):
        """Проверить наличие Reality настроек в конфигурации"""
        try:
            # Проверяем наличие метки [vl-no-ra] - исключаем такие конфигурации
            if "[vl-no-ra]" in config_str:
                return False
                
            # Проверяем наличие параметров Reality в строке
            reality_params = ['pbk=', 'sid=', 'spx=', 'fp=']
            if any(param in config_str for param in reality_params):
                return True
                
            # Декодируем конфигурацию для проверки JSON
            if "://" not in config_str:
                # Base64 конфигурация
                try:
                    decoded = base64.b64decode(config_str)
                    config_json = json.loads(decoded.decode('utf-8'))
                    
                    # Проверяем наличие Reality в streamSettings
                    stream_settings = config_json.get('streamSettings', {})
                    if stream_settings.get('security') == 'reality':
                        return True
                    if 'realitySettings' in stream_settings:
                        return True
                        
                    # Проверяем наличие TLS
                    if config_json.get('tls') == 'tls':
                        return True
                        
                except Exception as e:
                    self.add_log(f"Error decoding config: {e}", 'warning')
                    return False
            else:
                # URL конфигурация
                parsed = urlparse(config_str)
                query_params = parse_qs(parsed.query)
                
                # Проверяем наличие TLS
                if query_params.get('security', [''])[0] == 'tls':
                    return True
                    
                # Проверяем наличие параметров Reality
                reality_params = ['pbk', 'sid', 'spx', 'fp']
                if any(param in query_params for param in reality_params):
                    return True
                    
            return False
        except Exception as e:
            self.add_log(f"Error checking Reality settings: {e}", 'error')
            return False
        
    def filter_configs_by_flags(self, configs, flags):
        """Отфильтровать конфигурации по флагам и наличию Reality"""
        filtered = []
        self.add_log(f"Filtering by flags: {flags}")
        self.add_log("Only accepting Reality TLS configurations")
        self.add_log(f"Forbidden protocols: {FORBIDDEN_PROTOCOLS}")
        self.add_log(f"Forbidden transport types: {FORBIDDEN_TYPES}")
        
        for i, config in enumerate(configs, 1):
            if self.stop_event.is_set():
                self.add_log("Filtering interrupted by user", 'warning')
                break
                
            if not config.strip():
                continue
                
            # Проверка наличия Reality настроек
            if not self.has_reality_settings(config):
                self.add_log(f"[{i}] Skip: No Reality TLS settings", 'warning')
                continue
                
            if any(flag in config for flag in flags):
                try:
                    # Обработка base64 конфигураций
                    if "://" not in config:
                        try:
                            decoded = base64.b64decode(config)
                            config_json = json.loads(decoded.decode('utf-8'))
                            
                            remarks = config_json.get('ps', '')
                            address = config_json.get('add')
                            port = int(config_json.get('port', 443))
                            network = config_json.get('net', 'tcp')
                            
                            # Проверка флагов в remarks
                            if not any(flag in remarks for flag in flags):
                                continue
                                
                            # Проверка, что адрес - IP
                            if not address or not self.is_ip_address(address):
                                self.add_log(f"[{i}] Skip: not IP address: {address}", 'warning')
                                continue
                                
                            # Проверка типа транспорта
                            if network in FORBIDDEN_TYPES:
                                self.add_log(f"[{i}] Skip: forbidden transport type: {network}", 'warning')
                                continue
                                
                            # Проверка порта
                            if port in FORBIDDEN_PORTS:
                                self.add_log(f"[{i}] Skip: forbidden port: {port}", 'warning')
                                continue
                                
                            filtered.append(config)
                            self.add_log(f"[{i}] Found Reality config: {remarks[:50]}...", 'success')
                            
                        except Exception as e:
                            self.add_log(f"[{i}] Error processing base64 config: {e}", 'error')
                            continue
                    else:
                        # Обработка URL конфигураций
                        parsed = urlparse(config)
                        host = parsed.hostname
                        port = parsed.port
                        protocol = parsed.scheme.lower()
                        query_params = parse_qs(parsed.query)
                        
                        # Проверка на запрещенные протоколы
                        if protocol in FORBIDDEN_PROTOCOLS:
                            self.add_log(f"[{i}] Skip: forbidden protocol {protocol}", 'warning')
                            continue
                        
                        # Проверка типов транспорта
                        transport_type = None
                        if 'type' in query_params:
                            transport_type = query_params['type'][0].lower()
                        elif 'transportType' in query_params:
                            transport_type = query_params['transportType'][0].lower()
                        
                        if transport_type and transport_type in FORBIDDEN_TYPES:
                            self.add_log(f"[{i}] Skip: forbidden transport type: {transport_type}", 'warning')
                            continue
                        
                        if host and self.is_ip_address(host):
                            filtered.append(config)
                            self.add_log(f"[{i}] Found Reality config: {config[:50]}...", 'success')
                        else:
                            self.add_log(f"[{i}] Skip domain: {host}", 'warning')
                            
                except Exception as e:
                    self.add_log(f"[{i}] Processing error: {e}", 'error')
                    continue
        
        self.add_log(f"Filtered configurations: {len(filtered)}", 'success')
        return filtered
        
    def extract_address_and_config(self, config_uri):
        """Извлечь адрес и конфигурацию"""
        try:
            # Обработка base64 конфигураций
            if "://" not in config_uri:
                try:
                    decoded = base64.b64decode(config_uri)
                    config_json = json.loads(decoded.decode('utf-8'))
                    
                    address = config_json.get('add')
                    port = int(config_json.get('port', 443))
                    
                    if not address or not self.is_ip_address(address):
                        self.add_log(f"Skip domain name: {address}", 'warning')
                        return None, None
                    
                    if port in FORBIDDEN_PORTS:
                        self.add_log(f"Skip {address}:{port} - forbidden port", 'warning')
                        return None, None
                    
                    return f"{address}:{port}", config_uri
                    
                except Exception as e:
                    self.add_log(f"Error extracting from base64: {e}", 'error')
                    return None, None
            else:
                # Обработка URL конфигураций
                parsed = urlparse(config_uri)
                host = parsed.hostname
                port = parsed.port
                protocol = parsed.scheme.lower()
                
                if not self.is_ip_address(host):
                    self.add_log(f"Skip domain name: {host}", 'warning')
                    return None, None
                
                # Определение порта
                if not port:
                    query_params = parse_qs(parsed.query)
                    port = query_params.get('port')
                    if port:
                        try:
                            port = int(port[0])
                        except ValueError:
                            port = None
                    
                    if not port:
                        port = 443 if protocol in ('vless', 'vmess', 'trojan') else 8388
                
                # Фильтрация портов
                if port in FORBIDDEN_PORTS:
                    self.add_log(f"Skip {host}:{port} - forbidden port", 'warning')
                    return None, None
                
                if host and port:
                    address = f"{host}:{port}"
                    self.add_log(f"Found address: {address}", 'success')
                    return address, config_uri
                    
        except Exception as e:
            self.add_log(f"Address extraction error: {e}", 'error')
        
        return None, None
        
    def check_address_alive(self, address, timeout=5):
        """Проверить доступность адреса"""
        if self.stop_event.is_set():
            self.add_log("Check interrupted by user", 'warning')
            return False
            
        try:
            host, port = address.split(':')
            self.add_log(f"Checking availability {host}:{port}...")
            
            # Устанавливаем таймаут для сокета
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            
            with socket.create_connection((host, int(port)), timeout=timeout):
                self.add_log(f"Address {address} is available", 'success')
                return True
        except socket.timeout:
            self.add_log(f"Address {address} timeout after {timeout} seconds", 'warning')
            return False
        except Exception as e:
            self.add_log(f"Address {address} unavailable: {e}", 'error')
            return False
        finally:
            # Сбрасываем таймаут сокета
            socket.setdefaulttimeout(None)
            
    def process_configs(self):
        """Основной процесс обработки конфигураций"""
        start_time = datetime.now()
        self.add_log(f"Starting process: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stop_event.clear()
        
        # Шаг 1: Загрузка и фильтрация
        self.add_log("=" * 50)
        self.add_log("STEP 1: Downloading and filtering Reality TLS configurations")
        self.add_log("=" * 50)
        
        all_configs = self.download_config_list(CONFIG_URL)
        if not all_configs:
            self.add_log("Failed to download configuration list", 'error')
            return
        
        filtered_configs = self.filter_configs_by_flags(all_configs, FLAGS)
        
        if not filtered_configs:
            self.add_log("No Reality TLS configurations found with specified flags", 'error')
            return
        
        try:
            with open("filtered_configs.txt", 'w', encoding='utf-8') as f:
                f.write("\n".join(filtered_configs))
            self.add_log("Filtered configurations saved to filtered_configs.txt", 'success')
        except Exception as e:
            self.add_log(f"Error saving filtered configs: {e}", 'error')
        
        # Шаг 2: Проверка доступности
        self.add_log("\n" + "=" * 50)
        self.add_log("STEP 2: Checking address availability")
        self.add_log("=" * 50)
        
        self.alive_configs = []
        self.set_progress(0, len(filtered_configs))
        
        for i, config in enumerate(filtered_configs, 1):
            if self.stop_event.is_set():
                self.add_log("Process stopped by user", 'warning')
                break
                
            self.add_log(f"\n[{i}/{len(filtered_configs)}] Processing configuration...")
            address, full_config = self.extract_address_and_config(config)
            
            if not address:
                self.add_log("Failed to extract address from configuration", 'warning')
                continue
            
            if self.check_address_alive(address):
                self.alive_configs.append((address, full_config))
            
            self.set_progress(i, len(filtered_configs))
        
        if not self.alive_configs:
            self.add_log("No available addresses found", 'error')
            return
        
        try:
            with open("alive_configs.txt", 'w', encoding='utf-8') as f:
                for address, config in self.alive_configs:
                    f.write(f"{config}\n")
            
            self.add_log(f"\nAvailable configurations saved to alive_configs.txt (total: {len(self.alive_configs)})", 'success')
        except Exception as e:
            self.add_log(f"Error saving alive configs: {e}", 'error')
        
        end_time = datetime.now()
        duration = end_time - start_time
        self.add_log(f"\nCompleted: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_log(f"Total execution time: {str(duration).split('.')[0]}")
        self.add_log(f"Found available Reality TLS servers: {len(self.alive_configs)}", 'success')
        
    def start_process(self):
        """Запустить процесс обработки"""
        self.log_list.clear()
        self.alive_configs = []
        self.set_progress(0, 1)
        self.status_text.set_text("Processing...")
        self.run_in_thread(self.process_configs)
        
    def show_results(self):
        """Показать результаты проверки"""
        if not self.alive_configs:
            self.add_log("No results to display", 'warning')
            return
            
        results = []
        results.append(urwid.Text(('header', "Available Reality TLS Configurations:")))
        results.append(urwid.Divider())
        
        for address, config in self.alive_configs:
            results.append(urwid.Text(('success', f"✓ {address}")))
            results.append(urwid.Text(config[:100] + "..."))
            results.append(urwid.Divider())
        
        results.append(urwid.Text(f"Total: {len(self.alive_configs)} configurations"))
        
        list_walker = urwid.SimpleListWalker(results)
        list_box = urwid.ListBox(list_walker)
        
        overlay = urwid.Overlay(
            urwid.Frame(
                urwid.AttrMap(list_box, 'results'),
                footer=urwid.Text("Press ESC to close")
            ),
            self.main_widget,
            align='center',
            width=('relative', 80),
            valign='middle',
            height=('relative', 70)
        )
        
        self.loop.widget = overlay
        
    def exit_results_view(self):
        """Вернуться к основному интерфейсу"""
        self.loop.widget = self.main_widget
        
    def handle_input(self, input):
        """Обработка пользовательского ввода"""
        if input in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        elif input in ('r', 'R'):
            self.start_process()
        elif input in ('v', 'V'):
            self.show_results()
        elif input == 'esc':
            self.exit_results_view()
            
    def update_ui(self, loop, data):
        """Периодическое обновление интерфейса"""
        self.update_log_display()
        loop.set_alarm_in(0.1, self.update_ui)
        
    def run(self):
        """Запустить TUI приложение"""
        # Установка кодировки консоли для Windows
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleCP(65001)
                kernel32.SetConsoleOutputCP(65001)
            except Exception as e:
                self.add_log(f"Failed to set console encoding: {e}", 'warning')
        
        # Палитра цветов
        palette = [
            ('header', 'white', 'dark blue'),
            ('log_info', 'light gray', 'black'),
            ('log_success', 'light green', 'black'),
            ('log_error', 'light red', 'black'),
            ('log_warning', 'yellow', 'black'),
            ('progress', 'white', 'dark blue'),
            ('progress_normal', 'light gray', 'black'),
            ('results', 'black', 'light gray'),
        ]
        
        try:
            self.loop = urwid.MainLoop(
                self.main_widget,
                palette,
                unhandled_input=self.handle_input
            )
            
            self.loop.set_alarm_in(0.1, self.update_ui)
            self.loop.run()
        except KeyboardInterrupt:
            self.stop_event.set()
            self.add_log("Process interrupted by user. Stopping...", 'warning')
            # Не выходим, а продолжаем работу, чтобы пользователь мог увидеть сообщение
            time.sleep(1)  # Даем время на обновление интерфейса
        except Exception as e:
            self.add_log(f"Error running application: {e}", 'error')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    app = VlessCheckerTUI()
    app.run()