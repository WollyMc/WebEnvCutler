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
    download_path = os.path.abspath(os.path.join("Cutler", "Longleaf", "downloads"))

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }

    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=Service(driver_path), options=options)

commentary_pages = [
    ("https://southeasternasset.com/commentary/4q24-partners-fund-commentary/", "LLPF"),
    ("https://southeasternasset.com/commentary/4q24-small-cap-fund-commentary/", "LLSC"),
    ("https://southeasternasset.com/commentary/4q24-international-fund-commentary/", "LLIN"),
    ("https://southeasternasset.com/commentary/4q24-global-fund-commentary/", "LLGF"),
]

main_dir = os.path.join("Cutler", "Longleaf")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean up old PDFs
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

today = datetime.today().strftime("%Y%m%d")
driver = get_driver()
downloaded_files = []

for url, prefix in commentary_pages:
    try:
        print(f"\nVisiting: {url}")
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
        )

        anchors = driver.find_elements(By.TAG_NAME, "a")
        pdf_url = None
        for a in anchors:
            href = a.get_attribute("href")
            if href and ".pdf" in href:
                pdf_url = href
                break

        if not pdf_url:
            print(f"No PDF link found on page: {url}")
            continue

        print(f"Triggering download: {pdf_url}")
        driver.get(pdf_url)
        time.sleep(5)  # Wait for download to complete

    except Exception as e:
        print(f"Error processing {url}: {e}")

driver.quit()

# Merge all downloaded PDFs
pdf_paths = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]

if pdf_paths:
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merged_name = f"Longleaf_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(pdf_paths)} PDFs into: {merged_name}")
else:
    print("\nNo valid PDFs were downloaded.")
