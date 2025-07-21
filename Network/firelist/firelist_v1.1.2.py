import requests
import argparse
from urllib.parse import quote

# Константы по умолчанию
DEFAULT_ARCH = "win64"
DEFAULT_LANG = "en-US"
DEFAULT_TYPE = "msi"
BASE_FTP_URL = "https://ftp.mozilla.org/pub/firefox/releases/"

def get_firefox_versions(arch, lang, product_type):
    try:
        # Получаем данные версий
        response = requests.get("https://product-details.mozilla.org/1.0/firefox_versions.json")
        response.raise_for_status()
        versions = response.json()

        # Извлекаем версии
        latest_stable = versions["LATEST_FIREFOX_VERSION"]
        latest_esr = versions["FIREFOX_ESR"]
        latest_devel = versions.get("LATEST_FIREFOX_RELEASED_DEVEL_VERSION", None)

        # Функция для формирования корректной ссылки
        def build_download_url(version, arch, lang, product_type):
            base_path = f"{version}/{arch}/{lang}/"
            if product_type == "msi":
                filename = f"Firefox Setup {version}.msi"
            else:
                filename = f"Firefox Setup {version}.exe"
            
            # Кодируем пробелы и специальные символы в имени файла
            encoded_filename = quote(filename)
            return f"{BASE_FTP_URL}{base_path}{encoded_filename}"

        # Формируем ссылки
        stable_url = build_download_url(latest_stable, arch, lang, product_type)
        esr_url = build_download_url(latest_esr, arch, lang, product_type)
        devel_url = build_download_url(latest_devel, arch, lang, product_type) if latest_devel else None

        # Выводим результат
        print(f"Arch: {arch}, Lang: {lang}, Installer type: {product_type}\n")
        
        print(f"Current Stable: {latest_stable}")
        print(f"Download: {stable_url}\n")

        print(f"Current ESR: {latest_esr}")
        print(f"Download: {esr_url}\n")

        if latest_devel:
            print(f"Developer Edition: {latest_devel}")
            print(f"Download: {devel_url}")

    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Firefox Download Links Generator")
    parser.add_argument("--arch", help="Arch (win32/win64)", default=DEFAULT_ARCH)
    parser.add_argument("--lang", help="Language (en-US, ru и т.д.)", default=DEFAULT_LANG)
    parser.add_argument("--type", choices=["msi", "exe"], help="Installer type", default=DEFAULT_TYPE)

    args = parser.parse_args()
    get_firefox_versions(args.arch, args.lang, args.type)

if __name__ == "__main__":
    print()
    main()