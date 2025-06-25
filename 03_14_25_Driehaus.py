import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger, PdfReader
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Setup ===
script_dir = os.getcwd()
base_dir = os.path.join(script_dir, "Cutler", "Driehaus")
downloads_dir = os.path.join(base_dir, "downloads")
excerpted_dir = os.path.join(base_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

URL = "https://www.driehaus.com/fund-resources-results"

TARGET_TITLES = {
    "Driehaus Small Cap Growth Fund Annual Report: Investor Class",
    "Driehaus Emerging Markets Growth Fund Annual Report: Investor Class",
    "Driehaus Small Cap Growth Fund Annual Report: Institutional Class",
    "Driehaus Emerging Markets Growth Fund Annual Report: Institutional Class",
    "Driehaus International Developed Equity Fund Annual Report",
    "Driehaus Micro Cap Growth Fund Annual Report",
    "Driehaus International Small Cap Growth Fund Annual Report",
    "Driehaus Emerging Markets Small Cap Growth Fund Annual Report",
    "Driehaus Event Driven Fund Annual Report",
    "Driehaus Small/Mid Cap Growth Fund Annual Report",
    "Driehaus Global Fund Annual Report Annual Report"
}

# === Launch Chrome ===
options = uc.ChromeOptions()
driver = uc.Chrome(headless=True, options=options)
driver.get(URL)
time.sleep(5)

# === Parse HTML
soup = BeautifulSoup(driver.page_source, "html.parser")
rows = soup.select("table tbody tr")
downloaded = []

for row in rows:
    tds = row.find_all("td")
    if len(tds) < 3:
        continue

    title = tds[0].text.strip()
    date = tds[2].text.strip().lower()

    if title in TARGET_TITLES and date == "current":
        link_tag = tds[0].find("a")
        if not link_tag or not link_tag.get("href"):
            continue

        viewer_url = link_tag["href"]
        filename = title.replace(" ", "_").replace("/", "-") + ".pdf"
        filepath = os.path.join(downloads_dir, filename)

        try:
            # Open the viewer page
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(viewer_url)

            # Wait for the iframe or viewer to load
            iframe = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe"))
            )

            pdf_url = iframe.get_attribute("src")
            print(f" PDF iframe source: {pdf_url}")

            # Download the actual PDF
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": viewer_url
            }
            res = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
            content_type = res.headers.get("Content-Type", "")
            if "pdf" in content_type.lower():
                with open(filepath, "wb") as f:
                    f.write(res.content)
                print(f" Downloaded: {filename}")
                downloaded.append(filepath)
            else:
                print(f" Skipped (not a valid PDF): {filename} → {content_type}, {len(res.content)} bytes")

        except Exception as e:
            print(f" Error downloading {title}: {e}")
        finally:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

# === Merge all valid PDFs
valid_pdfs = []
for file in downloaded:
    try:
        PdfReader(file)
        valid_pdfs.append(file)
    except Exception as e:
        print(f" Skipped invalid PDF: {os.path.basename(file)} → {e}")

if valid_pdfs:
    merger = PdfMerger()
    for file in sorted(valid_pdfs):
        merger.append(file)
    merged_name = f"Driehaus_{datetime.today().strftime('%Y%m%d')}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(valid_pdfs)} PDFs → {merged_name}")
else:
    print("\n No valid PDFs to merge.")

driver.quit()
print("\n Driehaus scraping completed.")
