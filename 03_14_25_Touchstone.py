import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import httpx
from datetime import datetime
from PyPDF2 import PdfMerger

# === Setup Directories ===
today_str = datetime.today().strftime('%Y%m%d')
script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Touchstone")
DOWNLOAD_DIR = os.path.join(main_dir, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# === URL Constants ===
BASE_URL = "https://www.westernsouthern.com"
TOUCHSTONE_URL = f"{BASE_URL}/touchstone/mutual-funds"

def download_pdf(url, fund_name):
    try:
        filename = os.path.basename(urlparse(url).path.split("?")[0])
        output_path = os.path.join(DOWNLOAD_DIR, f"{fund_name} - {filename}")
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"[Touchstone] Downloaded: {output_path}")
            else:
                print(f"[Touchstone] Failed to download: {url} - Status: {response.status_code}")
    except Exception as e:
        print(f"[Touchstone] Error downloading {url}: {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, timeout=120000)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    session = requests.Session()

    print("[Touchstone] Opening mutual funds page using Playwright...")
    fund_links = []

    try:
        page.goto(TOUCHSTONE_URL, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)

        anchors = page.query_selector_all("a.ws-data-table__item-link")
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if href and "/touchstone/mutual-funds/" in href:
                full_url = urljoin(BASE_URL, href.split("#")[0])
                if full_url not in fund_links:
                    fund_links.append(full_url)

        print(f"[Touchstone] Found {len(fund_links)} fund pages.")
    except PlaywrightTimeout as e:
        print(f"[Touchstone] Failed to load main page: {e}")

    for fund_url in fund_links:
        print(f"[Touchstone] Visiting: {fund_url}")
        try:
            page.goto(fund_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            fund_soup = BeautifulSoup(page.content(), "html.parser")
            fund_name = fund_url.rstrip("/").split("/")[-1].replace("-", " ").title()

            for link in fund_soup.find_all("a", href=True):
                span = link.find("span")
                if span and "commentary" in span.get_text(strip=True).lower():
                    pdf_url = link["href"]
                    full_pdf_url = urljoin(BASE_URL, pdf_url)
                    download_pdf(full_pdf_url, fund_name)

        except PlaywrightTimeout:
            print(f"[Touchstone] Skipping due to timeout: {fund_url}")
        except Exception as e:
            print(f"[Touchstone] Error visiting {fund_url}: {e}")

    print("[Touchstone] Done.")
    browser.close()

# === Merge PDFs ===
pdf_files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith(".pdf")]

if pdf_files:
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merged_name = f"Touchstone_{today_str}_Merged.pdf"
    merged_path = os.path.join(DOWNLOAD_DIR, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(pdf_files)} PDFs into {merged_name}")
else:
    print("No Touchstone PDFs downloaded.")