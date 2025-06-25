import os
import time
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PyPDF2 import PdfMerger

# === Configuration ===
script_dir = os.getcwd()
driver_path = r"C:\chromedriver-win64\chromedriver.exe"
URL = "https://clipperfund.com/funds/clipper-fund/pm-review"

main_dir = os.path.join(script_dir, "Cutler", "Clipper")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clean old files
for file in os.listdir(downloads_dir):
    if file.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, file))
        print(f"Deleted: {file}")

# === Setup Selenium ===
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(driver_path), options=options)
driver.get(URL)
time.sleep(5)  # Let JS finish

# === Extract the download link directly using Selenium ===
downloaded_paths = []

try:
    links = driver.find_elements(By.TAG_NAME, "a")
    pdf_url = None
    for link in links:
        href = link.get_attribute("href")
        if href and "Download this Review" in link.text and href.endswith(".pdf"):
            pdf_url = href
            break

    if pdf_url:
        filename = os.path.basename(pdf_url)
        file_path = os.path.join(downloads_dir, filename)

        response = requests.get(pdf_url)
        with open(file_path, "wb") as f:
            f.write(response.content)

        downloaded_paths.append(file_path)
        print(f" Downloaded: {filename}")
    else:
        print(" Could not locate the PDF link via Selenium.")
except Exception as e:
    print(f" Error finding or downloading review: {e}")

driver.quit()

# === Merge the PDF ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"Clipper_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged into {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Clipper Fund commentary scraping completed.")
