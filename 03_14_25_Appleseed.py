import os
import time
from datetime import datetime
import cloudscraper
from bs4 import BeautifulSoup
import requests
from PyPDF2 import PdfMerger

# === Configuration ===
script_dir = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://appleseedfund.com"
START_URL = f"{BASE_URL}/perspectives/"

main_dir = os.path.join(script_dir, "Cutler", "Appleseed")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clear old PDFs
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old file: {file}")

# === Load and parse the page ===
scraper = cloudscraper.create_scraper()
response = scraper.get(START_URL)
soup = BeautifulSoup(response.text, "html.parser")

# === Find the first year row in the table (topmost <tr> with <strong>YEAR</strong>) ===
rows = soup.select("tbody tr")
latest_row = None
latest_year = None

for row in rows:
    year_cell = row.find("strong")
    if year_cell and year_cell.text.strip().isdigit():
        latest_row = row
        latest_year = year_cell.text.strip()
        break

if not latest_row or not latest_year:
    print(" Failed to find latest year row.")
    exit()

print(f" Found latest year: {latest_year}")

# === Extract PDF links from Semi-Annual and Annual ===
links = latest_row.find_all("a", href=True)
filtered = []

for a in links:
    label = a.text.strip().lower()
    if "semi" in label or "annual" in label:
        file_type = "SemiAnnual" if "semi" in label else "Annual"
        pdf_url = a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
        filtered.append((file_type, pdf_url))

# === Download PDFs ===
downloaded_paths = []

for file_type, url in filtered:
    filename = f"Appleseed_{file_type}_{latest_year}.pdf"
    file_path = os.path.join(downloads_dir, filename)

    try:
        resp = requests.get(url)
        with open(file_path, "wb") as f:
            f.write(resp.content)
        downloaded_paths.append(file_path)
        print(f" Downloaded: {filename}")
    except Exception as e:
        print(f" Failed to download {url}: {e}")

# === Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"Appleseed_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Appleseed Fund scraping and merging completed.")
