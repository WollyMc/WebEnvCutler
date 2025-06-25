import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# === Configuration ===
FUND_NAME = "Clarkston"
TARGET_URL = "https://www.clarkstonfunds.com/resources#factsheets-and-commentary"
base_dir = os.path.join("Cutler", FUND_NAME)
downloads_dir = os.path.join(base_dir, "downloads")
excerpted_dir = os.path.join(base_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# === Clean up old PDFs ===
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

prefs = {
    "download.default_directory": os.path.abspath(downloads_dir),
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(TARGET_URL)
time.sleep(5)

soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

# === Extract Commentary PDF Links ===
commentary_items = soup.find_all("li", attrs={"data-type": "comm"})
downloaded_paths = []

for i, li in enumerate(commentary_items, 1):
    a_tag = li.find("a", href=True)
    if not a_tag:
        continue
    pdf_url = a_tag["href"]
    if not pdf_url.endswith(".pdf"):
        continue

    title = a_tag.get("data-title") or a_tag.text.strip().replace(" ", "_")
    filename = f"Clarkston_{i:02d}_{title.replace('/', '_')}.pdf"
    file_path = os.path.join(downloads_dir, filename)

    try:
        resp = requests.get(pdf_url)
        with open(file_path, "wb") as f:
            f.write(resp.content)
        downloaded_paths.append(file_path)
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed to download {pdf_url}: {e}")

# === Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"Clarkston_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("\nNo PDFs were downloaded to merge.")

print("\nClarkston Funds commentary scraping completed.")
