import os
import time
import requests
import sys
import warnings
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright

# === Setup ===
BASE_URL = "https://www.saturna.com"
TARGET_URL = f"{BASE_URL}/insights/market-commentaries"
CUTOFF_DATE = datetime.today().replace(day=1) - timedelta(days=120)

script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Amana")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Use Selenium (UC) to bypass Cloudflare ===
print("Launching Selenium to bypass Cloudflare...")
uc_options = uc.ChromeOptions()
uc_options.headless = False
driver = uc.Chrome(options=uc_options)

print(f"Opening {TARGET_URL}")
driver.get(TARGET_URL)

try:
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.views-view-responsive-grid__item"))
    )
    print("Page content loaded, Cloudflare check passed.")
except Exception as e:
    print("Timed out waiting for page to load:", e)
    driver.quit()
    sys.exit(1)

# Extract cookies and user agent
selenium_cookies = driver.get_cookies()
user_agent = driver.execute_script("return navigator.userAgent;")
html = driver.page_source

# Suppress Windows resource warning and quit properly
if sys.platform.startswith("win"):
    warnings.filterwarnings("ignore", category=ResourceWarning)

driver.quit()
del driver

# === Step 2: Parse article links with BeautifulSoup ===
soup = BeautifulSoup(html, "html.parser")
blocks = soup.select("div.views-view-responsive-grid__item")
print(f"Found {len(blocks)} article blocks")

valid_links = []
for block in blocks:
    date_div = block.select_one("div.date")
    title_div = block.select_one("div.title")
    a_tag = block.select_one("a[href]")

    if not (date_div and title_div and a_tag):
        continue

    try:
        article_date = datetime.strptime(date_div.text.strip(), "%d %b %Y")
    except ValueError:
        continue

    if article_date >= CUTOFF_DATE:
        full_url = BASE_URL + a_tag["href"]
        label = title_div.text.strip().replace(" ", "_").replace("–", "-")
        date_str = article_date.strftime("%Y%m%d")
        valid_links.append((label, date_str, full_url))

print(f"{len(valid_links)} articles within last 4 months")

# === Step 3: Use Playwright to visit article pages and download PDFs ===
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
            print(f"Skipping cookie due to error: {e}")

    page = context.new_page()

    for label, date_str, article_url in valid_links:
        print(f"\nVisiting: {article_url}")
        try:
            page.goto(article_url, timeout=60000)
            time.sleep(2)
            article_html = page.content()
            article_soup = BeautifulSoup(article_html, "html.parser")

            pdf_links = article_soup.select("a[href$='.pdf']")
            if not pdf_links:
                print("No PDF links found.")
                continue

            for i, pdf_a in enumerate(pdf_links):
                href = pdf_a["href"]
                full_pdf_url = href if href.startswith("http") else BASE_URL + href
                filename = f"{label}_{date_str}_{i+1}.pdf"
                filepath = os.path.join(downloads_dir, filename)

                print(f"Downloading {full_pdf_url}")
                try:
                    response = requests.get(full_pdf_url, timeout=30)
                    if response.ok and response.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        print(f"Saved: {filename}")
                        downloaded_paths.append(filepath)
                    else:
                        print("Invalid PDF response or content type.")
                except Exception as e:
                    print(f"Failed to download: {e}")
        except Exception as e:
            print(f"Failed to load article page: {e}")

    browser.close()

# === Step 4: Merge downloaded PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Amana_{datetime.today().strftime('%Y%m%d')}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("No valid PDFs were downloaded.")
