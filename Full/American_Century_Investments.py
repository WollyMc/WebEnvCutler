import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests
from PyPDF2 import PdfMerger

# === Config ===
FUND_NAME = "American_Century_Investments"
BASE_DIR = os.path.join("Cutler", FUND_NAME)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# === Target Info ===
DOCUMENT_PAGE = "https://www.americancentury.com/insights/quarterly-performance-update/"

# === Launch Playwright ===
pdf_link = None
pdf_date_str = None

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(DOCUMENT_PAGE, timeout=60000)
    page.wait_for_timeout(4000)

    # Look for the actual hard-coded link to PDF (known from HTML structure)
    link_locator = page.locator("a[href$='quarterly-performance-update-web.pdf']")
    if link_locator.count() > 0:
        href = link_locator.first.get_attribute("href")
        if href:
            pdf_link = href if href.startswith("http") else f"https://www.americancentury.com{href}"

    # Use today's date as the fallback since PDF does not have an explicit date
    pdf_date_str = datetime.today().strftime("%Y%m%d")

    browser.close()

# === Download PDF ===
if pdf_link:
    filename = f"ACI_{pdf_date_str}_Quarterly_Performance_Update.pdf"
    filepath = os.path.join(DOWNLOADS_DIR, filename)

    try:
        response = requests.get(pdf_link, timeout=30)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed to download PDF: {e}")
else:
    print("No valid PDF link found.")

# === Merge if multiple PDFs exist (for core.py compatibility) ===
pdf_files = [os.path.join(DOWNLOADS_DIR, f) for f in os.listdir(DOWNLOADS_DIR) if f.endswith(".pdf")]
if len(pdf_files) > 1:
    merged_path = os.path.join(DOWNLOADS_DIR, f"{FUND_NAME}_Merged.pdf")
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(merged_path)
    merger.close()
    print(f"Merged PDF created: {merged_path}")
