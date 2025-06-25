import os
import time
import requests
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller

# === Setup Directories ===
script_dir = os.getcwd()
BASE_URL_MF = "https://www.cavanalhillfunds.com"
BASE_URL_SMA = "https://cavanalhillim.com"
MF_URL = f"{BASE_URL_MF}/insights-commentary/mutual-fund-commentary/"
SMA_URL = f"{BASE_URL_SMA}/insights-commentary/sma-commentary"

main_dir = os.path.join(script_dir, "Cutler", "CavanalHill")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clean up old PDFs
for file in os.listdir(downloads_dir):
    if file.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, file))
        print(f"Deleted: {file}")

# Auto-install correct version of ChromeDriver
chromedriver_autoinstaller.install()

# === Setup Selenium Driver ===
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    prefs = {
        "download.default_directory": downloads_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)

driver = get_driver()

# === Helper to wait for download completion ===
def wait_for_downloads(path, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        if not any(fname.endswith(".crdownload") for fname in os.listdir(path)):
            return True
        time.sleep(1)
    return False

# === Step 1: Mutual Fund Commentary (Top 7) ===
try:
    driver.get(MF_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "download")))
    mf_links = driver.find_elements(By.CLASS_NAME, "download")[:7]

    for i in range(len(mf_links)):
        driver.get(MF_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "download")))
        mf_links = driver.find_elements(By.CLASS_NAME, "download")[:7]

        link = mf_links[i]
        link.click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "btn"))).click()

        wait_for_downloads(downloads_dir)
        print(f" Downloaded Mutual Fund Report #{i+1}")
        time.sleep(1)
except Exception as e:
    print(f" Error in Mutual Fund Commentary: {e}")

# === Step 2: SMA Commentary (direct download) ===
try:
    driver.get(SMA_URL)
    WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "download")))
    time.sleep(1)

    sma_links = driver.find_elements(By.CLASS_NAME, "download")
    for link in sma_links:
        href = link.get_attribute("href")
        if href and href.endswith(".pdf"):
            print(f" Found SMA PDF link: {href}")
            pdf_data = requests.get(href, verify=False)
            today_str = datetime.today().strftime("%Y%m%d")
            filename = f"SMA_Commentary_{today_str}.pdf"
            file_path = os.path.join(downloads_dir, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_data.content)
            print(" Downloaded SMA Commentary via requests (SSL bypassed)")
            break
    else:
        print(" No SMA PDF links found.")
except Exception as e:
    print(f" Error in SMA Commentary: {e}")

driver.quit()

print("\n Cavanal Hill scraping completed. All files downloaded to:")
print(f" {downloads_dir}")

# === Merge all downloaded PDFs ===
pdf_files = [f for f in os.listdir(downloads_dir) if f.endswith(".pdf")]
if pdf_files:
    merger = PdfMerger()
    for pdf in sorted(pdf_files):
        merger.append(os.path.join(downloads_dir, pdf))

    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"CavanalHill_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(pdf_files)} PDFs into {merged_name}")
else:
    print("\n No PDFs were available to merge.")
