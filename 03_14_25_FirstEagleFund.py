import os
import time
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

def get_driver():
    driver_path = r"C:\chromedriver-win64\chromedriver.exe"
    download_path = os.path.abspath(os.path.join("Cutler", "FirstEagleFund", "downloads"))

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

# Setup folders
base_dir = os.path.join("Cutler", "FirstEagleFund")
downloads_dir = os.path.join(base_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clear previous downloads
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old file: {file}")

driver = get_driver()
today = datetime.today().strftime("%Y%m%d")

# Target URL
url = "https://www.firsteagle.com/first-eagle-fund-shareholder-reports"
driver.get(url)
time.sleep(3)

# Extract relevant PDFs
anchors = driver.find_elements(By.TAG_NAME, "a")
pdf_links = []

for a in anchors:
    href = a.get_attribute("href")
    if not href or not href.endswith(".pdf"):
        continue
    if href.startswith("/"):
        href = "https://www.firsteagle.com" + href

    filename = os.path.basename(href).lower()
    if any(kw in filename for kw in ["globalfund", "overseasfund", "usvaluefund", "goldfund"]) and (
        "tsr" in filename or "annual" in filename or "semi" in filename
    ):
        pdf_links.append(href)

print(f"\nFound {len(pdf_links)} relevant PDFs.")

# Download each PDF
downloaded = []
for link in pdf_links:
    filename = os.path.basename(link.split("?")[0])
    filepath = os.path.join(downloads_dir, filename)
    if os.path.exists(filepath):
        print(f"Already downloaded: {filename}")
        continue
    print(f"Downloading: {link}")
    driver.get(link)
    time.sleep(5)
    downloaded.append(filepath)

driver.quit()

# Merge all PDFs
time.sleep(2)
pdf_paths = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]

if pdf_paths:
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merged_name = f"FirstEagleFund_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(pdf_paths)} PDFs into: {merged_name}")
else:
    print("No valid PDFs were downloaded.")
