import time
import random
import re
import requests
import logging
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("registration.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_temp_email():
    """Mendapatkan email sementara dari generator.email"""
    try:
        key = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=2))
        response = requests.get(f"https://generator.email/search.php?key={key}", timeout=10)
        if response.ok:
            domains = response.json()
            if domains:
                email = f"test{random.randint(1000, 9999)}@{random.choice(domains)}"
                logging.info(f"📧 Email sementara: {email}")
                return email
    except Exception as e:
        logging.error(f"❌ Gagal mendapatkan email: {e}")
    return None

def register_account_selenium(email, password, referral_code):
    """Mendaftar akun menggunakan Selenium"""
    if not email:
        logging.warning("⚠️ Tidak bisa mendaftar karena email tidak diperoleh.")
        return False

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

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
    driver.quit()
    logging.info("✅ Akun berhasil didaftarkan, menunggu email verifikasi...")
    return True

def get_verification_link(email):
    """Mendapatkan link verifikasi dari email yang dikirim oleh no-reply@nvg8.io"""
    email_username, email_domain = email.split('@')
    cookies = {'embx': f'[%22{email}%22]', 'surl': f'{email_domain}/{email_username}'}
    headers = {'User-Agent': 'Mozilla/5.0'}

    for attempt in range(5):  # Maksimal 5x percobaan
        time.sleep(10)  # Tunggu 10 detik sebelum memeriksa email
        logging.info(f"🕒 Mencoba memeriksa email (Percobaan {attempt + 1}/5)...")
        response = requests.get("https://generator.email/inbox1/", headers=headers, cookies=cookies)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Cari email yang dikirim oleh no-reply@nvg8.io
            email_sender = soup.find(text=re.compile(r'no-reply@nvg8.io'))
            if email_sender:
                logging.info("📩 Email verifikasi ditemukan dari no-reply@nvg8.io")
                # Cari link verifikasi di dalam email
                verification_link = soup.find('a', href=re.compile(r'https://[^" ]+'))
                if verification_link:
                    link = verification_link['href']
                    logging.info(f"🔗 Link verifikasi ditemukan: {link}")
                    return link
                else:
                    logging.warning("⚠️ Link verifikasi tidak ditemukan dalam email.")
            else:
                logging.warning("⚠️ Email dari no-reply@nvg8.io belum ditemukan.")
        else:
            logging.error(f"❌ Gagal memeriksa inbox email: {response.status_code}")

    logging.error("❌ Gagal mendapatkan email verifikasi setelah 5 percobaan.")
    return None

def verify_account(verification_link):
    """Membuka link verifikasi menggunakan Selenium"""
    if not verification_link:
        logging.warning("⚠️ Tidak ada link verifikasi, tidak bisa lanjut.")
        return
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.get(verification_link)
    logging.info("✅ Akun berhasil diverifikasi!")
    time.sleep(5)
    driver.quit()

if __name__ == "__main__":
    jumlah_pendaftaran = int(input("Masukkan jumlah pendaftaran: "))
    referral_code = input("Masukkan referral code: ")

    for _ in range(jumlah_pendaftaran):
        logging.info("🚀 Memulai pendaftaran akun...")
        email = get_temp_email()
        password = "Test@1234"
        
        if email and register_account_selenium(email, password, referral_code):
            verification_link = get_verification_link(email)
            if verification_link:
                verify_account(verification_link)
            else:
                logging.error("⚠️ Pendaftaran gagal, tidak ada email verifikasi.")
        else:
            logging.error("❌ Gagal mendapatkan email sementara. Proses dihentikan.")