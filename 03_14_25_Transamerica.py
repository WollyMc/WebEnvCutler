import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright

# === Setup ===
BASE_URL = "https://www.transamerica.com"
TARGET_URL = f"{BASE_URL}/investments-fund-center"
today_str = datetime.today().strftime('%Y%m%d')

script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Transamerica")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Playwright - Navigate and Click Documents ===
print("Launching Playwright browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=150)
    context = browser.new_context()
    page = context.new_page()
    page.goto(TARGET_URL, timeout=60000)
    print("Page loaded.")

    # === Accept cookie banner if present ===
    try:
        page.locator("button:has-text('Allow all cookies')").click(timeout=5000)
        print("Cookie banner accepted.")
    except:
        print("No cookie banner detected or already dismissed.")

    # === Click on the 'Documents' tab ===
    try:
        # Wait for the element to be attached AND visible
        tab = page.locator("#tab-module-mf_documents")
        tab.wait_for(state="attached", timeout=15000)
        tab.wait_for(state="visible", timeout=15000)
        
        # Get element handle AFTER confirmed visible
        el = tab.element_handle()
        if el is None:
            raise Exception("Tab handle not found (null)")
        
        page.evaluate("""
            (el) => {
                el.scrollIntoView({behavior: 'auto', block: 'center'});
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            }
        """, el)
        
        print("Documents tab clicked using full event dispatch.")
        time.sleep(3)

    except Exception as e:
        print("Failed to switch to Documents tab:", e)
        browser.close()
        exit(1)


    # === Extract Commentary Links Using Playwright DOM ===
    print("Extracting download links directly from live DOM...")
    commentary_links = []

    anchors = page.locator("a[data-metrics-link-type='download']")
    count = anchors.count()
    print(f"Total download links found: {count}")

    for i in range(count):
        a = anchors.nth(i)
        href = a.get_attribute("href")
        title = a.get_attribute("data-metrics-link-dest")

        if title and "Commentary.pdf" in title and href and href.endswith(".pdf"):
            full_url = href if href.startswith("http") else BASE_URL + href
            commentary_links.append((title, full_url))

    print(f"Filtered Quarterly Commentary PDFs: {len(commentary_links)}")

    # === Download PDFs ===
    downloaded_paths = []
    for title, url in commentary_links:
        filename = title.replace(" ", "_")
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

    browser.close()

# === Step 2: Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Transamerica_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No valid Quarterly Commentary PDFs were downloaded.")
