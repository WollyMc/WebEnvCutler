import os
import time
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    driver_path = r"C:\chromedriver-win64\chromedriver.exe"
    download_path = os.path.abspath(os.path.join("Cutler", "Oakmark", "downloads"))

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }

    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(driver_path), options=options)

def wait_and_find(driver, by, value, timeout=15):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

def extract_pdf_from_commentary_page(driver, commentary_page_url):
    driver.get(commentary_page_url)
    try:
        pdf_link = wait_and_find(driver, By.XPATH, "//a[contains(@aria-label, 'Download PDF') and contains(@href, '.pdf')]").get_attribute("href")
        driver.get(pdf_link)
        print(f"Triggered download: {pdf_link}")
        time.sleep(5)
    except Exception as e:
        print(f"Could not extract PDF from: {commentary_page_url}\n{e}")

def extract_latest_commentary(driver, profile_url):
    try:
        driver.get(profile_url)
        wrapper = wait_and_find(driver, By.CSS_SELECTOR, "div.commentary.article-wrap div.content-wrapper")
        link = wrapper.find_element(By.TAG_NAME, "a").get_attribute("href")
        print(f"Found latest commentary for profile: {link}")
        extract_pdf_from_commentary_page(driver, link)
    except Exception as e:
        print(f"Error extracting from {profile_url}: {e}")

# Setup
base_dir = os.path.join("Cutler", "Oakmark")
downloads_dir = os.path.join(base_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean up old PDFs
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

today = datetime.today().strftime("%Y%m%d")
driver = get_driver()

# === PART 1: Main Fund Report ===
commentary_url = "https://oakmark.com/news-insights/commentary/"
try:
    driver.get(commentary_url)
    main_commentary = wait_and_find(driver, By.XPATH, "//a[contains(text(), 'Oakmark Fund:')]")
    main_link = main_commentary.get_attribute("href")
    extract_pdf_from_commentary_page(driver, main_link)
except Exception as e:
    print(f"Failed to extract main Oakmark report: {e}")

# === PART 2: Simplified Fixed Commentary Links ===
profiles = [
    "https://oakmark.com/who-we-are/our-team/bill-nygren/",
    "https://oakmark.com/who-we-are/our-team/david-herro/",
    "https://oakmark.com/who-we-are/our-team/adam-d-abbas/"
]

for profile in profiles:
    extract_latest_commentary(driver, profile)

driver.quit()

# === Merge PDFs ===
time.sleep(2)
pdf_paths = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]

if pdf_paths:
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merged_name = f"Oakmark_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"Merged {len(pdf_paths)} PDFs into: {merged_name}")
else:
    print("No valid PDFs were downloaded.")
