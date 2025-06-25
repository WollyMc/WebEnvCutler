import os
import time
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    driver_path = r"C:\chromedriver-win64\chromedriver.exe"
    download_path = os.path.abspath(os.path.join("Cutler", "Causeway", "downloads"))

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

# Setup
base_dir = os.path.join("Cutler", "Causeway")
downloads_dir = os.path.join(base_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean up old files
for f in os.listdir(downloads_dir):
    fp = os.path.join(downloads_dir, f)
    if os.path.isfile(fp) and f.endswith(".pdf"):
        os.remove(fp)
        print(f"Deleted: {f}")

driver = get_driver()
today = datetime.today().strftime("%Y%m%d")

url = "https://www.causewaycap.com/documents/#documents-global-value"
driver.get(url)
time.sleep(5)

# Fund sections to open (exact text on the site)
fund_sections = [
    "Global Value Fund",
    "International Value Fund",
    "Emerging Markets Fund",
    "International Opportunities Fund",
    "International Small Cap Fund"
]

# Expand each section
for section in fund_sections:
    try:
        header = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{section}')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", header)
        header.click()
        print(f"Expanded section: {section}")
        time.sleep(1)
    except Exception as e:
        print(f"Could not expand section '{section}': {e}")

# Extract all PDF links from the expanded page
anchors = driver.find_elements(By.TAG_NAME, "a")
pdf_links = []

relevant_keywords = [
    "summary",           # Summary Prospectus
    "investor",          # Investor Shares Profile Sheet
    "institutional",     # Institutional Shares Profile Sheet
    "flash",             # Flash Report
    "quarterly",         # Quarterly Report
    "semi"               # Semi Annual Report
]

excluded_keywords = ["form-crs", "adv", "brochure", "disclosure"]

for a in anchors:
    href = a.get_attribute("href")
    if not href or not href.endswith(".pdf"):
        continue

    filename = os.path.basename(href).lower()
    if any(ex in filename for ex in excluded_keywords):
        continue

    if any(kw in filename for kw in relevant_keywords):
        pdf_links.append(href)

print(f"\nFound {len(pdf_links)} relevant PDFs.")

# Download unique PDFs
for link in set(pdf_links):
    filename = os.path.basename(link.split("?")[0])
    filepath = os.path.join(downloads_dir, filename)
    if os.path.exists(filepath):
        print(f"Already downloaded: {filename} — skipping.")
        continue
    print(f"Downloading: {link}")
    driver.get(link)
    time.sleep(5)

driver.quit()

# Merge all PDFs
time.sleep(2)
pdfs = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]

if pdfs:
    merger = PdfMerger()
    for path in pdfs:
        merger.append(path)
    merged_name = f"Causeway_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(pdfs)} PDFs into: {merged_name}")
else:
    print("No valid PDFs were downloaded.")
