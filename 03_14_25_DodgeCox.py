import os
import time
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    driver_path = r"C:\chromedriver-win64\chromedriver.exe"
    download_path = os.path.abspath(os.path.join("Cutler", "Dodge&Cox", "downloads"))

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

# Setup
base_dir = os.path.join("Cutler", "Dodge&Cox")
downloads_dir = os.path.join(base_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clear old files
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

driver = get_driver()
today = datetime.today().strftime("%Y%m%d")

# === Step 1: Get strategy links from main page ===
main_url = "https://www.dodgeandcox.com/individual-investor/us/en/insights/2024-annual-investment-reviews.html"
driver.get(main_url)
time.sleep(2)

strategy_links = []
anchors = driver.find_elements(By.TAG_NAME, "a")
for a in anchors:
    href = a.get_attribute("href")
    if href and href.endswith("-strategy.html"):
        strategy_links.append(href)

print(f"\nFound {len(strategy_links)} strategy pages.")

# === Step 2: Visit each and download PDF ===
for link in strategy_links:
    try:
        print(f"\nVisiting strategy page: {link}")
        driver.get(link)

        # Wait and get the PDF anchor
        pdf_anchor = wait_and_find(driver, By.XPATH, "//a[contains(text(), 'Download PDF') and contains(@href, '.pdf')]")
        pdf_href = pdf_anchor.get_attribute("href")

        if pdf_href.startswith("/"):
            pdf_url = "https://www.dodgeandcox.com" + pdf_href
        else:
            pdf_url = pdf_href

        # Determine filename
        filename = os.path.basename(pdf_url.split("?")[0])
        filepath = os.path.join(downloads_dir, filename)

        if os.path.exists(filepath):
            print(f"Already downloaded: {filename} — skipping.")
            continue

        print(f"Downloading PDF: {pdf_url}")
        driver.get(pdf_url)
        time.sleep(5)  # Allow time for download

    except Exception as e:
        print(f"Failed to download from {link}: {e}")

driver.quit()

# === Step 3: Merge PDFs ===
time.sleep(2)
pdf_paths = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]

if pdf_paths:
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    merged_name = f"DodgeCox_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(pdf_paths)} PDFs into: {merged_name}")
else:
    print("No PDFs were downloaded.")
