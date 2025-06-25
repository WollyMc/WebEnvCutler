import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError

# === Configuration ===
script_dir = os.path.dirname(os.path.abspath(__file__))
driver_path = r"C:\chromedriver-win64\chromedriver.exe"
BASE_URL = "https://www.allianz.com"
START_URL = f"{BASE_URL}/en/economic_research/insights/publications.html"

# Use absolute paths regardless of where script is run from
main_dir = os.path.join(script_dir, "Cutler", "Allianz")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clean previous files
for f in os.listdir(downloads_dir):
    file_path = os.path.join(downloads_dir, f)
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"[WARNING] Could not remove {file_path}: {e}")

# === Chrome Options with download behavior ===
options = Options()
prefs = {
    "download.default_directory": os.path.abspath(downloads_dir),
    "plugins.always_open_pdf_externally": True,
    "download.prompt_for_download": False,
}
options.add_experimental_option("prefs", prefs)
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(service=Service(driver_path), options=options)

print("Starting Allianz scraping (first 6 articles)...")
driver.get(START_URL)

# === Step 1: Extract article URLs ===
article_links = []
try:
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    link_tags = soup.select("a.c-heading__link")

    for tag in link_tags:
        href = tag.get("href")
        if href:
            article_links.append(urljoin(BASE_URL, href))
        if len(article_links) == 6:
            break

    if not article_links:
        raise Exception("No article links found using a.c-heading__link.")

    print(f"   [✓] Found {len(article_links)} article links.")

except Exception as e:
    print(f"[ERROR] Failed to extract article links: {e}")
    driver.quit()
    exit()

pdf_files = []

# === Step 2: Visit articles and download PDFs via Selenium ===
for article_url in article_links:
    try:
        print(f"\nOpening article: {article_url}")
        driver.get(article_url)

        try:
            a_tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='link']//a[contains(@href, '.pdf')]"))
            )
            pdf_href = a_tag.get_attribute("href")
            full_pdf_url = urljoin(BASE_URL, pdf_href)

            filename = os.path.basename(full_pdf_url)
            local_path = os.path.join(downloads_dir, filename)

            print(f"   → Downloading via Selenium: {filename}")
            driver.get(full_pdf_url)

            # Wait up to 10 seconds for the file to appear
            for _ in range(10):
                if os.path.exists(local_path):
                    pdf_files.append(local_path)
                    print("   [✓] Download complete.")
                    break
                time.sleep(1)
            else:
                print("   [✗] File did not download.")

        except Exception as e:
            print(f"   [!] No PDF found in article: {e}")

    except Exception as e:
        print(f"[ERROR] Failed to process {article_url}: {e}")
        continue

driver.quit()

# === Step 3: Merge PDFs ===
print("\nMerging all valid PDFs...")
valid_files = []
for f in pdf_files:
    try:
        _ = PdfReader(f)
        valid_files.append(f)
    except PdfReadError:
        print(f"[SKIP] Corrupted file: {os.path.basename(f)}")
    except Exception as e:
        print(f"[ERROR] While checking {f}: {e}")

if valid_files:
    merger = PdfMerger()
    for f in valid_files:
        merger.append(f)
    merged_path = os.path.join(downloads_dir, "Allianz_Latest_6_Merged.pdf")
    merger.write(merged_path)
    merger.close()
    print(f"\n✅ Merged PDF saved: {merged_path}")
else:
    print("❌ No valid PDFs to merge.")

print("\n✅ Allianz scraping completed.")
