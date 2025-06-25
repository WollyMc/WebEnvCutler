import os
import time
import requests
from datetime import datetime
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError
from webdriver_manager.chrome import ChromeDriverManager  # Auto-manage ChromeDriver

# === Config ===
FUND_NAME = "Artisan"
script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", FUND_NAME)
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

base_url = "https://www.artisanpartners.com"
commentary_url = f"{base_url}/individual-investors/news-insights/thought-leadership/commentaries.html"

# Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
options.add_argument("--disable-web-security")
options.add_argument("--ignore-certificate-errors")
options.add_argument("user-agent=Mozilla/5.0")

# Get most recent 4 months
def get_recent_months(n=4):
    today = datetime.today()
    months = []
    for i in range(n):
        dt = datetime(today.year, today.month, 1)
        prev_month = (dt.month - i - 1) % 12 + 1
        year = dt.year - ((dt.month - i - 1) // 12)
        months.append(datetime(year, prev_month, 1).strftime("%b %Y"))
    return set(months)

recent_months = get_recent_months()
print("Recent months being checked:", recent_months)

# Delete old reports
for file in os.listdir(downloads_dir):
    if file.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, file))
        print(f"Deleted old report: {file}")

# Launch browser
print(f"Visiting: {commentary_url}")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(commentary_url)

pdf_count = 0

try:
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "holdings")))
    time.sleep(3)

    rows = driver.find_elements(By.XPATH, "//table[@id='holdings']//tr")
    if not rows:
        print("No rows found in #holdings table")
    else:
        print(f"Found {len(rows)} fund rows.")

    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue

        try:
            fund_link = cells[1].find_element(By.TAG_NAME, "a")
            fund_full = fund_link.get_attribute("title") or fund_link.text
        except:
            continue

        if "(" not in fund_full:
            continue

        fund_name = fund_full.split("(")[0].strip().replace(" ", "_")
        ticker = fund_full.split("(")[1].split(")")[0]

        for cell in cells[2:]:  # Skip first 2 columns
            try:
                link = cell.find_element(By.TAG_NAME, "a")
                label = link.text.strip()
                if label not in recent_months:
                    continue

                href = link.get_attribute("href")
                full_url = urljoin(base_url, href)
                print(f"\nLabel: {label} | Fund: {fund_name} ({ticker})")
                print(f"URL: {full_url}")

                pdf_name = f"Artisan_{label.replace(' ', '_')}_{fund_name}_{ticker}.pdf"
                pdf_path = os.path.join(downloads_dir, pdf_name)

                r = requests.get(full_url, timeout=30)
                print(f"Response: {r.status_code}, Size: {len(r.content)} bytes")
                if r.status_code == 200 and r.content:
                    with open(pdf_path, "wb") as f:
                        f.write(r.content)
                    print(f"Saved: {pdf_path}")
                    pdf_count += 1
                else:
                    print(f"Skipped: {pdf_name}")
            except:
                continue

finally:
    driver.quit()

# Final status
if pdf_count == 0:
    print("\nNo recent Artisan Monthly Commentaries downloaded.")
else:
    print(f"\nDone! {pdf_count} PDFs downloaded to: {downloads_dir}")

    # Merge all downloaded PDFs safely
    pdf_files = [
        os.path.join(downloads_dir, f)
        for f in os.listdir(downloads_dir)
        if f.endswith(".pdf")
    ]

    valid_pdfs = []
    for pdf_path in pdf_files:
        try:
            _ = PdfReader(pdf_path)
            valid_pdfs.append(pdf_path)
        except PdfReadError:
            print(f"[SKIP] Skipping corrupted file: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"[ERROR] Error checking {os.path.basename(pdf_path)}: {e}")

    if valid_pdfs:
        merger = PdfMerger()
        for pdf in valid_pdfs:
            merger.append(pdf)

        now = datetime.today()
        merged_name = f"Artisan_{now.strftime('%b_%Y')}_Merged.pdf"
        merged_path = os.path.join(downloads_dir, merged_name)

        merger.write(merged_path)
        merger.close()
        print(f"\nMerged PDF saved as: {merged_name}")
    else:
        print("No valid PDFs to merge.")
