import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Configuration ===
script_dir = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://www.bairdassetmanagement.com"
START_URL = f"{BASE_URL}/insights/#category=cat-11568"

main_dir = os.path.join(script_dir, "Full", "Cutler", "Baird")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clear old PDFs
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

# === Setup Selenium ===
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(START_URL)
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "card")))

soup = BeautifulSoup(driver.page_source, "html.parser")
cards = soup.select("a.card")

target_cards = []
for card in cards:
    title_tag = card.select_one("span.card-title")
    if not title_tag:
        continue

    title = title_tag.text.strip()
    if "2025" in title and "International and Global Growth Fund Commentary" in title:
        relative_link = card["href"]
        detail_url = relative_link if relative_link.startswith("http") else BASE_URL + relative_link
        target_cards.append((title, detail_url))

print(f" Found {len(target_cards)} relevant 2025 commentary articles.")

# === Visit detail pages and download PDFs ===
downloaded_paths = []
for i, (title, detail_url) in enumerate(target_cards, start=1):
    print(f"\n Visiting: {detail_url}")
    try:
        driver.get(detail_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "btn")))
        page_soup = BeautifulSoup(driver.page_source, "html.parser")

        pdf_btn = page_soup.find("a", class_="btn", string=lambda t: t and "READ FULL" in t.upper())
        if not pdf_btn:
            print(" PDF link button not found.")
            continue

        pdf_url = pdf_btn["href"]
        if not pdf_url.startswith("http"):
            pdf_url = BASE_URL + pdf_url

        filename = f"Baird_2025_Q{i}.pdf"
        file_path = os.path.join(downloads_dir, filename)

        pdf_resp = requests.get(pdf_url)
        with open(file_path, "wb") as f:
            f.write(pdf_resp.content)
        downloaded_paths.append(file_path)
        print(f" Downloaded: {filename}")

    except Exception as e:
        print(f" Failed to process {detail_url}: {e}")

driver.quit()

# === Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"Baird_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Baird 2025 Commentary scraping and merging completed.")
