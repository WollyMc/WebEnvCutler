import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright

# === Setup Directories ===
BASE_URL = "https://www.virtus.com"
FUND_LISTING_URL = f"{BASE_URL}/our-products/individual-investors/mutual-funds#/type.daily/relation.nav/asset_sub_class.null"

today_str = datetime.today().strftime('%Y%m%d')
script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Virtus")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Use Selenium to Get Cookies + User Agent ===
print("[Virtus] Opening fund listing page...")
uc_options = uc.ChromeOptions()
uc_options.headless = False
driver = uc.Chrome(version_main=136, options=uc_options)
driver.get(FUND_LISTING_URL)

WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "js-daily-performance")))
time.sleep(3)

selenium_cookies = driver.get_cookies()
user_agent = driver.execute_script("return navigator.userAgent;")
driver.quit()

# === Step 2: Use Playwright to Get Real Fund URLs (Visible in Daily tab only) ===
fund_links = set()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(user_agent=user_agent)

    for cookie in selenium_cookies:
        try:
            context.add_cookies([{
                "name": cookie['name'],
                "value": cookie['value'],
                "domain": cookie['domain'].lstrip('.'),
                "path": cookie['path'],
                "expires": cookie.get('expiry'),
                "httpOnly": cookie['httpOnly'],
                "secure": cookie['secure'],
                "sameSite": "Lax"
            }])
        except Exception as e:
            print(f"[Cookie] Skipped: {e}")

    page = context.new_page()
    page.goto(FUND_LISTING_URL, timeout=60000)
    page.wait_for_selector("#js-daily-performance", timeout=15000)
    time.sleep(2)

    # Only select fund rows in the visible "Daily" table
    rows = page.query_selector_all("#js-daily-performance tbody tr")
    for row in rows:
        anchor = row.query_selector("a")
        if anchor:
            visible = page.evaluate("el => el.offsetParent !== null", anchor)
            if visible:
                href = anchor.get_attribute("href")
                if href and "/products/" in href:
                    full_url = href if href.startswith("http") else BASE_URL + href
                    fund_links.add(full_url)

    print(f"[Virtus] Found {len(fund_links)} unique fund pages.")

    # === Step 3: Download Quarterly Commentary PDFs ===
    downloaded_paths = []

    for i, fund_url in enumerate(sorted(fund_links), 1):
        print(f"[{i}/{len(fund_links)}] {fund_url}")
        try:
            page.goto(fund_url, timeout=60000)
            time.sleep(2)
            soup = BeautifulSoup(page.content(), "html.parser")

            # Target the Marketing Materials block
            # Search all tables that might include commentary PDFs
            tables = soup.find_all("table")
            for table in tables:
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    if not cells or len(cells) < 2:
                        continue
                    description = cells[0].get_text(strip=True).lower()
                    if "commentary" not in description:
                        continue
                    link_tag = row.select_one("a.file[href$='.pdf']")
                    if not link_tag:
                        continue
                    href = link_tag.get("href", "")
                    if href.startswith("mailto:") or not href.endswith(".pdf"):
                        continue
                    full_url = href if href.startswith("http") else BASE_URL + href
                    filename = full_url.split("/")[-1]
                    filepath = os.path.join(downloads_dir, filename)

                    print(f"[Download] {filename}")
                    try:
                        r = requests.get(full_url, timeout=30)
                        if r.ok and r.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                            with open(filepath, "wb") as f:
                                f.write(r.content)
                            downloaded_paths.append(filepath)
                        else:
                            print("Skipped: Not a valid PDF.")
                    except Exception as e:
                        print(f"Failed download: {e}")

        except Exception as e:
            print(f"Error scraping {fund_url}: {e}")

    browser.close()

# === Step 4: Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for pdf in downloaded_paths:
        merger.append(pdf)
    merged_name = f"Virtus_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No Quarterly Commentary PDFs downloaded.")
