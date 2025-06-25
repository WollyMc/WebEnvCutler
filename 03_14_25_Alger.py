import os
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError
import undetected_chromedriver as uc

# === Paths ===
DOWNLOAD_DIR = os.path.join("Cutler", "Alger", "downloads")
MERGED_PDF = os.path.join(DOWNLOAD_DIR, "Alger_Merged.pdf")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# === Setup Selenium ===
options = uc.ChromeOptions()
# options.add_argument('--headless')  # Uncomment to run headless
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')

driver = uc.Chrome(options=options)
wait = WebDriverWait(driver, 20)

try:
    # === Load page ===
    url = "https://www.alger.com/Pages/StrategyFinder.aspx?vehicle=mf"
    driver.get(url)

    # === Click the 'Literature' radio button ===
    radio_button = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio'][value='show-doc']"))
    )
    driver.execute_script("arguments[0].click();", radio_button)
    time.sleep(3)  # Allow DOM to update

    # === Wait for document section to load ===
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.ft-doc")))

    # === Collect all commentary links ===
    links = driver.find_elements(By.CSS_SELECTOR, "td.ft-doc a[target='_blank']")
    commentary_links = []
    for link in links:
        text = link.text.strip().lower()
        href = link.get_attribute("href")
        if text.endswith("commentary") and href and href.endswith(".pdf"):
            commentary_links.append((text, href))

    print(f"\n Found {len(commentary_links)} commentary PDFs.")
finally:
    driver.quit()

# === Download PDFs ===
downloaded_files = []
for idx, (label, href) in enumerate(commentary_links, start=1):
    try:
        response = requests.get(href, timeout=10)
        if "pdf" not in response.headers.get("Content-Type", "").lower() or not response.content.startswith(b"%PDF"):
            print(f"  Invalid PDF at: {href}")
            continue
        file_name = f"{idx:02d}_{label.replace(' ', '_')}.pdf"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"  Downloaded: {file_name}")
        downloaded_files.append(file_path)
    except Exception as e:
        print(f"  Failed to download {href}: {e}")

# === Merge Valid PDFs ===
valid_files = []
if downloaded_files:
    merger = PdfMerger()
    for f in downloaded_files:
        try:
            PdfReader(f)  # Validate before merging
            merger.append(f)
            valid_files.append(f)
        except PdfReadError:
            print(f"  Skipped corrupted PDF: {f}")
            os.remove(f)
        except Exception as e:
            print(f"  Error appending {f}: {e}")
    if valid_files:
        merger.write(MERGED_PDF)
        merger.close()
        print(f"\n Merged PDF saved at: {MERGED_PDF}")
    else:
        print(" All PDFs were invalid. Nothing merged.")
else:
    print(" No PDFs downloaded.")
