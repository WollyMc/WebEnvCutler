import os
import time
import requests
from datetime import datetime
from PyPDF2 import PdfMerger
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Config ===
URL = "https://www.williamblairfunds.com/literature/fund-literature/manager-commentaries/"
base_url = "https://www.williamblairfunds.com"

main_dir = os.path.join("Cutler", "WilliamBlair")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# === Clean old PDFs ===
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))
        print(f"Deleted: {f}")

# === Setup undetected ChromeDriver ===
options = uc.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(options=options)

# === Load Page ===
driver.get(URL)
time.sleep(10) 

# === Wait for all <a> links to appear on the page ===
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
    )
    print(" Anchor tags loaded.")
except Exception as e:
    print(" Anchors not found. Saving page.")
    with open("william_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.quit()
    exit()

# === Extract PDF links from all <a> tags ===
anchors = driver.find_elements(By.TAG_NAME, "a")
pdf_links = []
for a in anchors:
    href = a.get_attribute("href")
    if href and "commentary-fundid" in href and href.endswith(".pdf"):
        full_url = href if href.startswith("http") else f"{base_url}{href}"
        pdf_links.append(full_url)

# Save full HTML for inspection
with open("william_debug.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("Saved full HTML snapshot to william_debug.html")
driver.quit()
exit()

# === Download PDFs ===
pdf_paths = []
for link in pdf_links:
    filename = os.path.basename(link.split("?")[0])
    file_path = os.path.join(downloads_dir, filename)
    try:
        print(f"Downloading: {filename}")
        r = requests.get(link, timeout=20)
        with open(file_path, "wb") as f:
            f.write(r.content)
        pdf_paths.append(file_path)
    except Exception as e:
        print(f" Failed to download {filename}: {e}")

driver.quit()

# === Merge PDFs ===
if pdf_paths:
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    today = datetime.today().strftime("%Y%m%d")
    merged_name = f"WilliamBlair_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(pdf_paths)} PDFs into: {merged_name}")
else:
    print(" No PDFs downloaded. Merge skipped.")
