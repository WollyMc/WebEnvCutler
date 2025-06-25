import os
import requests
from datetime import datetime
from urllib.parse import urljoin
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright

# === Setup Paths ===
MAIN_URL = "https://wasatchglobal.com/mutual-fund-performance-overviews/"
today_str = datetime.today().strftime('%Y%m%d')


script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Wasatch")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean old files
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Navigate and collect only U.S. Mutual Fund links ===
print("Launching Playwright and loading Wasatch fund overview page...")

with sync_playwright() as p:
    headless_mode = os.environ.get("HEADLESS_MODE", "true").lower() == "true"
    browser = p.chromium.launch(headless=headless_mode, slow_mo=0 if headless_mode else 150)
    #browser = p.chromium.launch(headless=False, slow_mo=150)
    context = browser.new_context()
    page = context.new_page()
    page.goto(MAIN_URL, wait_until="domcontentloaded", timeout=120000)

    print("Main page loaded.")
    fund_links = page.locator("div.table__col--26-5 a.fundLink")
    count = fund_links.count()
    print(f"Found {count} fund links. Filtering for U.S. Mutual Funds...")

    # Only these tickers will be visited
    valid_us_funds = {
        "WGROX", "WHOSX", "WALSX", "WMICX", "WAMVX",
        "WAAEX", "WMCVX", "WAUSX", "WAMCX"
    }

    filtered_links = []
    for i in range(count):
        link = fund_links.nth(i)
        ticker = link.inner_text().strip()
        if ticker in valid_us_funds:
            href = link.get_attribute("href")
            if href:
                filtered_links.append((ticker, href))

    print(f"Matched {len(filtered_links)} U.S. Mutual Fund links.")

    # === Step 2: Visit each and collect commentary PDFs ===
    pdf_links = []

    for ticker, href in filtered_links:
        try:
            print(f"Visiting fund page for: {ticker} → {href}")
            new_page = context.new_page()
            new_page.goto(href, wait_until="domcontentloaded", timeout=60000)

            # Locate and filter links to commentary PDFs
            commentary_links = new_page.locator("a:has(span:text('Commentary'))")
            c_count = commentary_links.count()

            for j in range(c_count):
                a = commentary_links.nth(j)
                file_href = a.get_attribute("href")
                if file_href and "Commentary" in file_href and file_href.endswith(".pdf"):
                    full_url = file_href if file_href.startswith("http") else urljoin(href, file_href)
                    title = f"{ticker}_Commentary"
                    pair = (title, full_url)
                    if pair not in pdf_links:
                        pdf_links.append(pair)
                        print(f"  Found: {full_url}")

            new_page.close()

        except Exception as e:
            print(f"  Failed to process {ticker}: {e}")

    browser.close()

print(f"\nFinal count of unique PDFs to download: {len(pdf_links)}")

# === Step 3: Download PDFs ===
downloaded_paths = []

for title, url in pdf_links:
    filename = title.replace(" ", "_").replace("/", "-") + ".pdf"
    filepath = os.path.join(downloads_dir, filename)
    print(f"Downloading: {url}")

    try:
        response = requests.get(url, timeout=30)
        if response.ok and response.headers.get("Content-Type", "").lower().startswith("application/pdf"):
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Saved: {filename}")
            downloaded_paths.append(filepath)
        else:
            print("Invalid PDF response.")
    except Exception as e:
        print(f"Failed to download: {e}")

# === Step 4: Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Wasatch_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No valid PDFs were downloaded.")
