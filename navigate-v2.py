import time
import random
import re
import requests
import logging
import sys
import tempfile
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("registration.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Counter untuk menyimpan jumlah akun berhasil dan gagal
success_count = 0
fail_count = 0
lock = threading.Lock()  # Lock untuk menghindari race condition

def get_temp_email():
    """Mendapatkan email sementara dari generator.email"""
    try:
        key = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=2))
        response = requests.get(f"https://generator.email/search.php?key={key}", timeout=10)
        if response.ok:
            domains = response.json()
            if domains:
                email = f"test{random.randint(1000, 9999)}@{random.choice(domains)}"
                logging.info(f"[≈] Email sementara: {email}")
                return email
    except Exception as e:
        logging.error(f"[X] Gagal mendapatkan email: {e}")
    return None

def register_account_selenium(email, password, referral_code):
    """Mendaftar akun menggunakan Selenium"""
    if not email:
        logging.warning("[!] Tidak bisa mendaftar karena email tidak diperoleh.")
        return False

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        logging.info("[@] Membuka halaman pendaftaran...")
        driver.get("https://dataquest.nvg8.io/signup")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.NAME, "referral").send_keys(referral_code)

        sign_up_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", sign_up_button)
        time.sleep(1)
        sign_up_button.click()

        time.sleep(5)
        logging.info("[✓] Akun berhasil didaftarkan, menunggu email verifikasi...")
        return True
    except Exception as e:
        logging.error(f"[X] Terjadi kesalahan saat mendaftar: {e}")
        return False
    finally:
        driver.quit()
        logging.info("[×] WebDriver ditutup.")

def get_verification_link(email):
    """Mendapatkan link verifikasi dari email yang dikirim oleh no-reply@nvg8.io"""
    email_username, email_domain = email.split('@')
    cookies = {'embx': f'[%22{email}%22]', 'surl': f'{email_domain}/{email_username}'}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for attempt in range(5):
        time.sleep(10)
        logging.info(f"[≈] Mencoba memeriksa email (Percobaan {attempt + 1}/5)...")
        response = requests.get("https://generator.email/inbox1/", headers=headers, cookies=cookies)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            email_sender = soup.find(string=re.compile(r'no-reply@nvg8.io'))
            if email_sender:
                logging.info("[✓] Email verifikasi ditemukan dari no-reply@nvg8.io")
                verification_link = soup.find('a', href=re.compile(r'https://[^" ]+'))
                if verification_link:
                    link = verification_link['href']
                    logging.info(f"[✓] Link verifikasi ditemukan: {link}")
                    return link
                else:
                    logging.warning("[!] Link verifikasi tidak ditemukan dalam email.")
            else:
                logging.warning("[!] Email dari no-reply@nvg8.io belum ditemukan.")
        else:
            logging.error(f"[X] Gagal memeriksa inbox email: {response.status_code}")

    logging.error("[X] Gagal mendapatkan email verifikasi setelah 5 percobaan.")
    return None

def verify_account(verification_link):
    """Membuka link verifikasi menggunakan Selenium"""
    if not verification_link:
        logging.warning("[!] Tidak ada link verifikasi, tidak bisa lanjut.")
        return False
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(verification_link)
        logging.info("[✓] Akun berhasil diverifikasi!")
        time.sleep(5)
        return True
    except Exception as e:
        logging.error(f"[X] Gagal memverifikasi akun: {e}")
        return False
    finally:
        driver.quit()
        logging.info("[×] WebDriver ditutup.")

def process_registration(referral_code):
    """Fungsi yang dijalankan di setiap thread"""
    global success_count, fail_count

    logging.info("[≈] Memulai pendaftaran akun...")
    email = get_temp_email()
    password = "Test@1234"
    
    if email and register_account_selenium(email, password, referral_code):
        verification_link = get_verification_link(email)
        if verification_link and verify_account(verification_link):
            with lock:
                success_count += 1
        else:
            with lock:
                fail_count += 1
            logging.error("[!] Pendaftaran gagal, tidak ada email verifikasi.")
    else:
        with lock:
            fail_count += 1
        logging.error("[X] Gagal mendapatkan email sementara. Proses dihentikan.")

if __name__ == "__main__":
    jumlah_pendaftaran = int(input("Masukkan jumlah pendaftaran: "))
    max_threads = int(input("Masukkan jumlah thread maksimal (1-10): "))

    if max_threads < 1 or max_threads > 10:
        logging.error("[X] Jumlah thread tidak valid, gunakan angka antara 1-10.")
        sys.exit(1)

    referral_code = input("Masukkan referral code: ")

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(process_registration, referral_code) for _ in range(jumlah_pendaftaran)]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"[X] Error dalam thread: {e}")

    # Menampilkan ringkasan hasil pendaftaran
    logging.info("="*50)
    logging.info(f"Akun yang berhasil didaftarkan: {success_count}")
    logging.info(f"Akun yang gagal didaftarkan   : {fail_count}")
    logging.info("="*50)
