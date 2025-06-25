import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger

from playwright.sync_api import sync_playwright

# === Setup Directories ===
today_str = datetime.today().strftime('%Y%m%d')
script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "ValueLine")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

BASE_URL = "https://vlfunds.com"
COMMENTARY_URL = f"{BASE_URL}/news/commentary"

print("[ValueLine] Launching browser to scrape latest commentaries...")

latest_pdfs = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(COMMENTARY_URL, timeout=60000)
    page.wait_for_selector(".col-xs-12", timeout=10000)
    time.sleep(1)

    soup = BeautifulSoup(page.content(), "html.parser")
    sections = soup.find_all("div", class_="col-xs-12")

    for section in sections:
        fund_name = section.find("h2")
        if not fund_name:
            continue

        fund_title = fund_name.text.strip()
        link = section.find("ul", class_="lit-list").find("a", href=True)
        if link and link["href"].endswith(".pdf"):
            pdf_url = link["href"]
            full_url = pdf_url if pdf_url.startswith("http") else BASE_URL + pdf_url
            filename = full_url.split("/")[-1]
            filepath = os.path.join(downloads_dir, filename)

            print(f"[Download] {fund_title} => {filename}")
            try:
                r = requests.get(full_url, timeout=30)
                if r.ok:
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    latest_pdfs.append(filepath)
            except Exception as e:
                print(f"Failed to download {full_url}: {e}")

    browser.close()

# === Merge PDFs ===
if latest_pdfs:
    merger = PdfMerger()
    for pdf in latest_pdfs:
        merger.append(pdf)
    merged_name = f"ValueLine_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(latest_pdfs)} PDFs into {merged_name}")
else:
    print("No Value Line PDFs downloaded.")
