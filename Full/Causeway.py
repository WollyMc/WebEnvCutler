import os
import time
import chromedriver_autoinstaller
from datetime import datetime
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Setup Directories ===
FUND_NAME = "Causeway"
base_dir = os.path.join("Cutler", FUND_NAME)
downloads_dir = os.path.join(base_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# === Auto-Download Correct ChromeDriver ===
chromedriver_autoinstaller.install()

# === Configure Driver ===
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    prefs = {
        "download.default_directory": os.path.abspath(downloads_dir),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)

# === Clean Old Files ===
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))
        print(f"Deleted: {f}")

# === Download PDFs ===
driver = get_driver()
today = datetime.today().strftime("%Y%m%d")

url = "https://www.causewaycap.com/documents/#documents-global-value"
driver.get(url)
time.sleep(5)

fund_sections = [
    "Global Value Fund",
    "International Value Fund",
    "Emerging Markets Fund",
    "International Opportunities Fund",
    "International Small Cap Fund"
]

for section in fund_sections:
    try:
        header = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{section}')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", header)
        header.click()
        print(f"Expanded: {section}")
        time.sleep(1)
    except Exception as e:
        print(f" Failed to expand {section}: {e}")

anchors = driver.find_elements(By.TAG_NAME, "a")
pdf_links = []

relevant_keywords = ["summary", "investor", "institutional", "flash", "quarterly", "semi"]
excluded_keywords = ["form-crs", "adv", "brochure", "disclosure"]

for a in anchors:
    href = a.get_attribute("href")
    if not href or not href.endswith(".pdf"):
        continue
    filename = os.path.basename(href).lower()
    if any(x in filename for x in excluded_keywords):
        continue
    if any(k in filename for k in relevant_keywords):
        pdf_links.append(href)

print(f"\n Found {len(pdf_links)} relevant PDFs.")

# === Download PDFs ===
for link in set(pdf_links):
    filename = os.path.basename(link.split("?")[0])
    file_path = os.path.join(downloads_dir, filename)
    if os.path.exists(file_path):
        print(f"Already exists: {filename}")
        continue
    print(f"Downloading: {filename}")
    driver.get(link)
    time.sleep(5)

driver.quit()

# === Merge PDFs ===
time.sleep(2)
pdfs = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf")]
if pdfs:
    merger = PdfMerger()
    for path in pdfs:
        merger.append(path)
    merged_file = os.path.join(downloads_dir, f"{FUND_NAME}_{today}_Merged.pdf")
    merger.write(merged_file)
    merger.close()
    print(f"\n Merged {len(pdfs)} PDFs into: {merged_file}")
else:
    print(" No PDFs downloaded to merge.")
