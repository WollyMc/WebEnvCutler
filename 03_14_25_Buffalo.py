import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
import cloudscraper

# === Configuration ===
script_dir = os.getcwd()
BASE_URL = "https://buffalofunds.com"
START_URL = f"{BASE_URL}/our-funds/performance/#literature"

main_dir = os.path.join(script_dir, "Cutler", "Buffalo")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clear old PDFs
for file in os.listdir(downloads_dir):
    if file.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, file))
        print(f"Deleted old file: {file}")

# === Scrape PDF Link ===
scraper = cloudscraper.create_scraper()
response = scraper.get(START_URL)
soup = BeautifulSoup(response.text, "html.parser")

annual_link = None
for a in soup.find_all("a", href=True):
    if "annual report" in a.get_text(strip=True).lower() and a["href"].endswith(".pdf"):
        annual_link = a
        break

downloaded_paths = []
if annual_link and annual_link.get("href", "").endswith(".pdf"):
    pdf_url = annual_link["href"]
    if not pdf_url.startswith("http"):
        pdf_url = BASE_URL + pdf_url

    today_str = datetime.today().strftime("%Y%m%d")
    filename = f"Buffalo_AnnualReport_{today_str}.pdf"
    file_path = os.path.join(downloads_dir, filename)

    try:
        pdf_resp = scraper.get(pdf_url)
        with open(file_path, "wb") as f:
            f.write(pdf_resp.content)
        downloaded_paths.append(file_path)
        print(f" Downloaded: {filename}")
    except Exception as e:
        print(f" Failed to download {pdf_url}: {e}")
else:
    print(" Annual Report PDF link not found.")

# === Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    merged_name = f"Buffalo_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Buffalo Funds scraping and merging completed.")
