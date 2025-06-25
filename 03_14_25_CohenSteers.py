import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger
import requests

# === Configuration ===
script_dir = os.getcwd()
driver_path = r"C:\chromedriver-win64\chromedriver.exe"
BASE_URL = "https://www.cohenandsteers.com/funds/?type=mutual-funds#overview"
main_dir = os.path.join(script_dir, "Cutler", "CohenSteers")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# === Clean up old PDFs ===
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

# === Setup Selenium WebDriver ===
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
prefs = {
    "download.default_directory": downloads_dir,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True,
}
options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(service=Service(driver_path), options=options)
driver.get(BASE_URL)

# === Role Modal ===
try:
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Financial Professional')]"))
    ).click()
    print(" Clicked through role modal")
except:
    print(" Role modal not shown or already dismissed.")

# === Wait for the fund table to load ===
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.fund-table tbody tr"))
    )
    print(" Fund table rows are now visible.")
except:
    print(" Still no table rows found. Exiting.")
    driver.quit()
    exit()

# === Extract all commentary PDF links from table using JS ===
commentary_links = driver.execute_script("""
  const links = [];
  const rows = document.querySelectorAll("table.fund-table tbody tr");
  rows.forEach(row => {
    const cells = row.querySelectorAll("td");
    if (cells.length >= 8) {
      const fundName = cells[0].innerText.trim().replace(/\s+/g, '_').replace(/\//g, '-');
      const commentaryCell = cells[cells.length - 1];
      const aTag = commentaryCell.querySelector("a[href$='.pdf']");
      if (aTag) {
        links.push({ name: fundName, url: aTag.href });
      }
    }
  });
  return links;
""")

if not commentary_links:
    print(" No commentary links found after table load. Exiting.")
    driver.quit()
    exit()

print(f" Found {len(commentary_links)} commentary PDFs.")

# === Download PDFs ===
downloaded = 0
for item in commentary_links:
    name, url = item['name'], item['url']
    filename = f"{name}_Commentary.pdf"
    filepath = os.path.join(downloads_dir, filename)

    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            downloaded += 1
            print(f" Downloaded: {filename}")
        else:
            print(f" Failed to download: {filename} → HTTP {response.status_code}")
    except Exception as e:
        print(f" Error downloading {filename}: {e}")

# === Merge downloaded PDFs ===
if downloaded:
    merger = PdfMerger()
    for file in sorted(os.listdir(downloads_dir)):
        if file.endswith(".pdf"):
            merger.append(os.path.join(downloads_dir, file))
    merged_name = f"CohenSteers_{datetime.today().strftime('%Y%m%d')}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {downloaded} files → {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Cohen & Steers commentary scraping completed.")
driver.quit()