import requests
import json
import time
import random
import base64
import os
from datetime import datetime, timezone, timedelta
from colorama import init, Fore, Style

# Inisialisasi Colorama untuk kompatibilitas lintas platform
init()

# URL dasar API
base_user_url = "https://api.w3bflix.world/v1/users/"
base_luckydraw_url = "https://api.w3bflix.world/v1/users/{}/luckydraw"

# Daftar model perangkat untuk variasi
device_models = [
    "Pixel 5", "Pixel 6", "Pixel 7", "SM-G975F", "SM-G998B", "SM-A525F",
    "Redmi Note 10", "Vivo V20", "POCO X4 Pro", "OnePlus 9", "Nokia 6.2",
    "Realme 9 Pro", "Mi 11", "Oppo Reno4", "Xperia 1 IV", "Samsung A52",
    "Huawei P40 Lite", "Vivo Y70s", "Moto G Power"
]

# Fungsi untuk menghasilkan User-Agent Telegram
def generate_telegram_user_agent():
    telegram_versions = [f"10.{x}.{y}" for x in range(0, 15) for y in range(0, 2)]
    android_versions = [f"{x}" for x in range(10, 15)]
    sdk_versions = [str(x) for x in range(29, 35)]
    
    version = random.choice(telegram_versions)
    android = random.choice(android_versions)
    sdk = random.choice(sdk_versions)
    model = random.choice(device_models)
    
    return f"Telegram/{version} (Android {android}; SDK {sdk}; {model})"

# Fungsi untuk mengelola User-Agent
def load_user_agents():
    try:
        with open("user_agents.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_agents(user_agents):
    with open("user_agents.json", "w") as f:
        json.dump(user_agents, f, indent=2)

def get_user_agent(user_id):
    user_agents = load_user_agents()
    if user_id not in user_agents:
        user_agents[user_id] = generate_telegram_user_agent()
        save_user_agents(user_agents)
    return user_agents[user_id]

# Fungsi untuk mengonversi TONWallet (base64) ke format hex address (0:xxx)
def ton_wallet_to_hex(ton_wallet):
    try:
        wallet_bytes = base64.b64decode(ton_wallet)
        hex_address = "0:" + wallet_bytes.hex()
        return hex_address
    except Exception:
        return None

# Fungsi untuk menghitung sisa waktu hingga 00:00 UTC berikutnya
def get_time_until_reset():
    now = datetime.now(timezone.utc)
    next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    time_diff = next_reset - now
    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return hours, minutes

# Fungsi untuk menghitung sisa waktu hingga waktu tertentu
def get_time_until(target_time):
    now = datetime.now(timezone.utc)
    time_diff = target_time - now
    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return hours, minutes, seconds

# Fungsi untuk format waktu yang friendly
def format_wait_time(hours, minutes, seconds=0):
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")
    return " ".join(time_parts) if time_parts else "0s"

# Fungsi untuk menghitung waktu reset harian
def get_next_reset():
    now = datetime.now(timezone.utc)
    next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return next_reset

# Fungsi untuk menghitung waktu draw acak setelah reset
def get_next_draw_time():
    now = datetime.now(timezone.utc)
    next_reset = get_next_reset()
    # Draw acak antara 01:00 UTC (08:00 WIB) dan 16:00 UTC (23:00 WIB)
    random_seconds = random.randint(3600, 57600)  # 1 jam hingga 16 jam
    draw_time = next_reset + timedelta(seconds=random_seconds)
    return draw_time

# Fungsi untuk menampilkan countdown
def display_countdown(target_time):
    while datetime.now(timezone.utc) < target_time:
        hours, minutes, seconds = get_time_until(target_time)
        print(f"\r{Fore.YELLOW}Waktu Draw: {target_time.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')} | Sisa Waktu: {format_wait_time(hours, minutes, seconds)}{Style.RESET_ALL}", end="")
        time.sleep(1)
    print()  # Baris baru setelah countdown selesai

# Fungsi untuk melakukan POST request ke user update
def update_user(user_id):
    url = f"{base_user_url}{user_id}"
    headers = {
        "User-Agent": get_user_agent(user_id),
        "Accept-Language": "en-US,en;q=0.9",
        "X-Telegram-Version": get_user_agent(user_id).split("Telegram/")[1].split(" ")[0],
        "X-Api-Key": "vL7wcDNndYZOA5fLxtab33wUAAill6Kk"
    }
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(url, json={}, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            elif response.status_code == 429:
                sleep_time = 2 ** attempt
                log_result(f"Rate limit untuk Akun ID {user_id}, retry setelah {sleep_time}s")
                time.sleep(sleep_time)
                continue
            else:
                error_msg = f"Status Code {response.status_code}: {response.text}"
                log_result(f"User update gagal untuk Akun ID {user_id}: {error_msg}")
                if response.status_code == 403:
                    log_result(f"Saran: Periksa apakah ID {user_id} valid.")
                return False, error_msg
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            log_result(f"User update gagal untuk Akun ID {user_id}: {error_msg}")
            return False, error_msg
    return False, "Gagal setelah retry"

# Fungsi untuk melakukan POST request ke lucky draw
def lucky_draw(user_id, wallet_address=None):
    url = base_luckydraw_url.format(user_id)
    payload = {"type": "ton"}
    if wallet_address:
        payload["address"] = wallet_address
    headers = {
        "User-Agent": get_user_agent(user_id),
        "Accept-Language": "en-US,en;q=0.9",
        "X-Telegram-Version": get_user_agent(user_id).split("Telegram/")[1].split(" ")[0],
        "X-Api-Key": "vL7wcDNndYZOA5fLxtab33wUAAill6Kk"
    }
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return True, data
            elif response.status_code == 429:
                sleep_time = 2 ** attempt
                log_result(f"Rate limit untuk Akun ID {user_id} (lucky draw), retry setelah {sleep_time}s")
                time.sleep(sleep_time)
                continue
            else:
                error_msg = f"Status Code {response.status_code}: {response.text}"
                log_result(f"Lucky draw gagal untuk Akun ID {user_id}: {error_msg}")
                if response.status_code == 403:
                    log_result(f"Saran: Periksa apakah ID {user_id} valid.")
                return False, error_msg
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            log_result(f"Lucky draw gagal untuk Akun ID {user_id}: {error_msg}")
            return False, error_msg
    return False, "Gagal setelah retry"

# Fungsi untuk logging ke file dan konsol
def log_result(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("api_log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# Fungsi untuk menampilkan output dengan style dan warna
def print_styled_output(user_id, first_name, balance, user_result, lucky_result, wallet_address):
    print(f"{Fore.WHITE}-------{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Akun ID: {user_id} ({first_name}){Style.RESET_ALL}")
    balance_color = Fore.GREEN if balance != "Unknown" else Fore.RED
    print(f"{balance_color}Balance: {balance}{Style.RESET_ALL}")
    
    lucky_success, lucky_data = lucky_result
    print("Lucky Draw:")
    hours, minutes = get_time_until_reset()
    wait_time = format_wait_time(hours, minutes)
    
    if lucky_success:
        if lucky_data.get("data", {}).get("rewards") is not None:
            rewards = lucky_data["data"]["rewards"]
            yields = lucky_data["data"]["yields"]
            print(f"  {Fore.GREEN}Berhasil!{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}Hadiah: {rewards} poin{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}Yield: {yields}{Style.RESET_ALL}")
            print(f"  Wallet: {wallet_address if wallet_address else 'Tidak terkoneksi'}")
            print(f"  {Fore.BLUE}User-Agent: {get_user_agent(user_id)}{Style.RESET_ALL}")
        else:
            print(f"  {Fore.YELLOW}Sudah draw hari ini!{Style.RESET_ALL}")
            print(f"  Pesan: Tunggu {wait_time} untuk kesempatan berikutnya")
            print(f"  Wallet: {wallet_address if wallet_address else 'Tidak terkoneksi'}")
            print(f"  {Fore.BLUE}User-Agent: {get_user_agent(user_id)}{Style.RESET_ALL}")
    else:
        print(f"  {Fore.RED}Gagal: {lucky_data}{Style.RESET_ALL}")
        print(f"  Wallet: {wallet_address if wallet_address else 'Tidak terkoneksi'}")
        print(f"  {Fore.BLUE}User-Agent: {get_user_agent(user_id)}{Style.RESET_ALL}")
    
    print(f"{Fore.WHITE}-------{Style.RESET_ALL}")

# Membaca ID dari file id.txt dan memproses
def process_accounts():
    try:
        with open('id.txt', 'r') as file:
            user_ids = [line.strip() for line in file if line.strip()]
        
        if not user_ids:
            log_result("File id.txt kosong atau tidak ada ID valid!")
            return

        log_result(f"Memproses {len(user_ids)} akun...")
        
        for user_id in user_ids:
            user_result = update_user(user_id)
            first_name = "(Unknown)"
            balance = "Unknown"
            if user_result[0]:
                user_data = user_result[1]
                first_name = user_data.get("data", {}).get("user", {}).get("FirstName", "(Unknown)")
                balance = user_data.get("data", {}).get("user", {}).get("Balance", "Unknown")
            
            wallet_address = None
            lucky_result = (False, "User update gagal, skip lucky draw")
            if user_result[0]:
                ton_wallet = user_data.get("data", {}).get("user", {}).get("TONWallet")
                if ton_wallet:
                    wallet_address = ton_wallet_to_hex(ton_wallet)
                lucky_result = lucky_draw(user_id, wallet_address)
            
            print_styled_output(user_id, first_name, balance, user_result, lucky_result, wallet_address)
            time.sleep(random.uniform(1, 3))

    except FileNotFoundError:
        log_result("File id.txt tidak ditemukan!")
    except Exception as e:
        log_result(f"Error saat membaca file: {str(e)}")

# Jalankan script dengan looping
if __name__ == "__main__":
    # Clear terminal sekali saat script dimulai
    os.system("cls" if os.name == "nt" else "clear")
    while True:
        log_result("🚀 Mulai menjalankan script...")
        print(f"\n{Fore.CYAN}🌟 Memulai Pemrosesan Multi-Akun 🌟{Style.RESET_ALL}\n")
        process_accounts()
        log_result("🏁 Selesai memproses semua akun.")
        print(f"\n{Fore.CYAN}🌟 Pemrosesan Selesai! 🌟{Style.RESET_ALL}\n")
        
        next_draw_time = get_next_draw_time()
        log_result(f"Waktu draw berikutnya: {next_draw_time.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"\n{Fore.CYAN}🌟 Menunggu Draw Berikutnya 🌟{Style.RESET_ALL}")
        display_countdown(next_draw_time)
        # Clear terminal sebelum loop berikutnya
        os.system("cls" if os.name == "nt" else "clear")