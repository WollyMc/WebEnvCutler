import os
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError

# Configuration
driver_path = r"C:\chromedriver-win64\chromedriver.exe"
tickers = ["CMCAX", "GRF", "IIGF", "MWMF", "EMBF", "CCIF"]
doc_types = {
    "summary": "Summary_Prospectus",
    "annual": "Annual_Report",
    "commentary": "Commentary",
    "holdings": "Holdings_Overview"
}
base_page = "https://vaneck.onlineprospectus.net/vaneck/{ticker}/index.php?ctype={doc}"

# Directory setup
main_dir = os.path.join("Cutler", "VanEck")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Setup Selenium
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(service=Service(driver_path), options=options)

downloaded_files = []

for ticker in tickers:
    for short_doc, doc_label in doc_types.items():
        url = base_page.format(ticker=ticker, doc=short_doc)
        print(f"\nVisiting: {url}")
        try:
            driver.get(url)

            # Try waiting for download link
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "book_download_lnk"))
                )
                time.sleep(1)
            except Exception:
                print(f"[SKIP] No download links found for {ticker} ({doc_label})")
                continue

            # Extract actual download links
            download_links = driver.find_elements(By.CLASS_NAME, "book_download_lnk")
            for link in download_links:
                href = link.get_attribute("href")
                title = link.get_attribute("title")
                if href and href.endswith(".pdf") and "Download" in title:
                    filename = f"VanEck_{ticker}_{doc_label}.pdf"
                    filepath = os.path.join(downloads_dir, filename)

                    print(f"→ Downloading: {filename}")
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "Referer": url
                    }

                    try:
                        r = requests.get(href, headers=headers, timeout=30)
                        if r.status_code == 200 and r.content:
                            with open(filepath, "wb") as f:
                                f.write(r.content)
                            downloaded_files.append(filepath)
                        else:
                            print(f"[SKIP] Empty or failed response: {filename}")
                    except Exception as e:
                        print(f"[ERROR] Could not download {filename} — {e}")
        except Exception as e:
            print(f"[ERROR] Ticker {ticker}, Doc {short_doc}: {e}")
            continue

driver.quit()

# Merge all valid PDFs
print("\nMerging valid PDFs...")
valid_files = []
for fpath in downloaded_files:
    try:
        _ = PdfReader(fpath)
        valid_files.append(fpath)
    except PdfReadError:
        print(f"[SKIP] Corrupted file skipped: {os.path.basename(fpath)}")
    except Exception as e:
        print(f"[ERROR] Failed to check {fpath}: {e}")

if valid_files:
    merger = PdfMerger()
    for pdf in valid_files:
        merger.append(pdf)

    now = datetime.today()
    merged_filename = f"VanEck_{now.strftime('%b_%Y')}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_filename)

    merger.write(merged_path)
    merger.close()
    print(f"\n Merged PDF saved as: {merged_path}")
else:
    print(" No valid PDFs to merge.")

print("\n VanEck scraping completed.")
