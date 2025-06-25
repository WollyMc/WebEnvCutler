import os
import time
import sys
import warnings
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright
import subprocess
import platform

# === ChromeDriver Setup ===
def get_installed_chrome_version():
    try:
        if platform.system() == "Windows":
            stream = os.popen(r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version')
            output = stream.read()
            version_line = [line for line in output.split('\n') if "version" in line.lower()]
            if version_line:
                return version_line[0].split()[-1]
        else:
            result = subprocess.run(["google-chrome", "--version"], stdout=subprocess.PIPE)
            return result.stdout.decode("utf-8").strip().split()[-1]
    except Exception:
        return None

def setup_driver():
    chrome_version = get_installed_chrome_version()
    if chrome_version:
        major_version = chrome_version.split('.')[0]
        print(f"Detected Chrome version: {chrome_version}")
    else:
        print("Could not detect Chrome version. Assuming version 114+")
        major_version = "114"  # fallback if detection fails

    options = uc.ChromeOptions()
    options.headless = False
    return uc.Chrome(version_main=int(major_version), options=options)

# === Config ===
FUND_NAME = "Ariel"
BASE_URL = "https://www.arielinvestments.com"
SEARCH_URL = f"{BASE_URL}/?site-search-term=commentary&type=product"

today_str = datetime.today().strftime('%Y%m%d')
script_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(script_dir, "Cutler", FUND_NAME)
downloads_dir = os.path.join(BASE_DIR, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clean old PDFs
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Use Selenium to Extract All Product Links from Paginated Search ===
print("Launching Selenium to fetch product links...")
driver = setup_driver()

product_links = []
visited_pages = set()
current_url = SEARCH_URL

try:
    while current_url:
        print(f"Loading search page: {current_url}")
        driver.get(current_url)
        WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "search-item")))
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        search_items = soup.select("div.search-item a.product.standard")

        for tag in search_items:
            href = tag.get("href")
            full_url = href if href.startswith("http") else BASE_URL + href
            if full_url not in product_links:
                product_links.append(full_url)

        print(f"Found {len(search_items)} product links on this page")

        # Find "Next" button
        next_page = soup.select_one("a.ar-pagination-btn-next")
        if next_page and 'href' in next_page.attrs:
            next_href = next_page['href']
            current_url = next_href if next_href.startswith("http") else BASE_URL + next_href
            if current_url in visited_pages:
                break
            visited_pages.add(current_url)
        else:
            break

except Exception as e:
    print(f"Error during pagination: {e}")

# Collect cookies and user-agent before quitting
selenium_cookies = driver.get_cookies()
user_agent = driver.execute_script("return navigator.userAgent;")

if sys.platform.startswith("win"):
    warnings.filterwarnings("ignore", category=ResourceWarning)

driver.quit()
del driver

print(f"Total unique product pages collected: {len(product_links)}")

# === Step 2: Use Playwright to Visit Each Product Page and Download Quarterly Commentary PDFs ===
downloaded_paths = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=200)
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
            print(f"Skipping cookie: {e}")

    page = context.new_page()

    for product_url in product_links:
        print(f"\nVisiting product page: {product_url}")
        try:
            page.goto(product_url, timeout=60000)
            time.sleep(2)

            page_html = page.content()
            soup = BeautifulSoup(page_html, "html.parser")

            commentary_links = soup.select("a.reusable-link.standard")

            found = False
            for link in commentary_links:
                text_tag = link.select_one("span.ar-download-title-text")
                if text_tag and "Quarterly Commentary" in text_tag.text:
                    pdf_href = link.get("href")
                    if not pdf_href or not pdf_href.endswith(".pdf"):
                        continue
                    full_pdf_url = pdf_href if pdf_href.startswith("http") else BASE_URL + pdf_href
                    filename = full_pdf_url.split("/")[-1]
                    filepath = os.path.join(downloads_dir, filename)

                    print(f"Downloading Quarterly Commentary: {full_pdf_url}")
                    try:
                        response = requests.get(full_pdf_url, timeout=30)
                        if response.ok and response.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                            with open(filepath, "wb") as f:
                                f.write(response.content)
                            downloaded_paths.append(filepath)
                            print(f"Saved: {filename}")
                            found = True
                        else:
                            print("Invalid PDF response.")
                    except Exception as e:
                        print(f"Failed to download: {e}")

            if not found:
                print("No Quarterly Commentary PDF found on this page.")

        except Exception as e:
            print(f"Failed to process product page: {e}")

    browser.close()

# === Step 3: Merge Downloaded PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Ariel_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No valid Quarterly Commentary PDFs were downloaded.")
