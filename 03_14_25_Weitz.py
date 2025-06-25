import os
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright

# === Setup Paths ===
URL = "https://weitzinvestments.com/perspectives/commentary/default.fs"
BASE_URL = "https://weitzinvestments.com"
today_str = datetime.today().strftime('%Y%m%d')

script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Weitz")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean old files
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Load site and expand accordions ===
print("Launching Playwright to scrape Weitz commentary page...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=150)
    context = browser.new_context()
    page = context.new_page()
    page.goto(URL, timeout=120000)
    print("Page loaded.")

    # Click all visible accordion toggles
    toggles = page.locator("h3[data-bs-toggle='collapse']")
    count = toggles.count()
    print(f"Found {count} accordion toggles.")

    for i in range(count):
        toggle = toggles.nth(i)
        try:
            toggle.scroll_into_view_if_needed()
            toggle.click()
            print(f"Expanded: {toggle.inner_text()}")
            time.sleep(1)
        except Exception as e:
            print(f"Failed to expand section {i}: {e}")

    # Get all <a> tags inside .collapse.show
    links = page.locator(".collapse.show a")
    total_links = links.count()
    print(f"Found {total_links} total links inside expanded sections.")

    pdf_links = []
    for i in range(total_links):
        a = links.nth(i)
        href = a.get_attribute("href")
        if href and ".pdf" in href:
            full_url = urljoin(BASE_URL, href)
            title = a.inner_text().strip().replace(" ", "_").replace("/", "-")
            pdf_links.append((title, full_url))

    print(f"Filtered {len(pdf_links)} valid PDF links.")
    browser.close()

# === Step 2: Download PDFs ===
downloaded_paths = []
for title, url in pdf_links:
    filename = title + ".pdf"
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

# === Step 3: Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Weitz_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No valid PDFs were downloaded.")
