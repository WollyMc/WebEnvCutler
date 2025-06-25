import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
import cloudscraper

# === Configuration ===
script_dir = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://bn.brookfield.com"
annual_url = f"{BASE_URL}/reports-filings/annual-reports"
letter_url = f"{BASE_URL}/reports-filings/letters-shareholders"

main_dir = os.path.join(script_dir, "Cutler", "Brookfield")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clear old PDFs
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

scraper = cloudscraper.create_scraper()
downloaded_paths = []

def find_latest_pdf(soup, label_text=None):
    links = soup.find_all("a", href=True)
    year_to_url = {}

    for link in links:
        href = link["href"]
        text = link.get_text(strip=True).lower()
        full_text = text + " " + href

        if not href.endswith(".pdf"):
            continue

        match = re.search(r"/(20\d{2})/", href)
        if not match:
            continue
        year = int(match.group(1))

        if label_text and label_text not in full_text:
            continue

        year_to_url[year] = href

    if not year_to_url:
        return None, None

    latest_year = max(year_to_url.keys())
    return latest_year, BASE_URL + year_to_url[latest_year]

# === Process Annual Report ===
try:
    res = scraper.get(annual_url)
    soup = BeautifulSoup(res.text, "html.parser")
    year, pdf_url = find_latest_pdf(soup, label_text="full annual report")
    if year and pdf_url:
        filename = f"Brookfield_AnnualReport_{year}.pdf"
        path = os.path.join(downloads_dir, filename)
        with open(path, "wb") as f:
            f.write(scraper.get(pdf_url).content)
        downloaded_paths.append(path)
        print(f" Downloaded: {filename}")
    else:
        print(" No annual report found.")
except Exception as e:
    print(f" Failed to process annual reports: {e}")

# === Process Letter to Shareholders ===
try:
    res = scraper.get(letter_url)
    soup = BeautifulSoup(res.text, "html.parser")
    year, pdf_url = find_latest_pdf(soup, label_text="letter-to-shareholders")
    if year and pdf_url:
        filename = f"Brookfield_ShareholderLetter_{year}.pdf"
        path = os.path.join(downloads_dir, filename)
        with open(path, "wb") as f:
            f.write(scraper.get(pdf_url).content)
        downloaded_paths.append(path)
        print(f" Downloaded: {filename}")
    else:
        print(" No shareholder letter found.")
except Exception as e:
    print(f" Failed to process shareholder letters: {e}")

# === Merge PDFs ===
if downloaded_paths:
    merger = PdfMerger()
    for path in downloaded_paths:
        merger.append(path)
    today_str = datetime.today().strftime("%Y%m%d")
    merged_name = f"Brookfield_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\n Merged {len(downloaded_paths)} PDFs into {merged_name}")
else:
    print("\n No PDFs were downloaded to merge.")

print("\n Brookfield report scraping and merging completed.")
