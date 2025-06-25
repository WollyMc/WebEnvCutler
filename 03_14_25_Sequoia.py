import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import cloudscraper
from PyPDF2 import PdfMerger

# Set up folders
main_dir = os.path.join("Cutler", "Sequoia")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)
os.makedirs(excerpted_dir, exist_ok=True)

# Clear old files
for file in os.listdir(downloads_dir):
    path = os.path.join(downloads_dir, file)
    if os.path.isfile(path) and file.endswith(".pdf"):
        os.remove(path)
        print(f"Deleted old report: {file}")

# Download page HTML using CloudScraper to bypass Cloudflare protection
url = "https://www.sequoiafund.com/resources/"
scraper = cloudscraper.create_scraper()
response = scraper.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# Find all anchor tags with PDF links
pdf_tags = soup.find_all("a", href=True)
pdf_links = {}
today = datetime.today().strftime("%Y%m%d")

for tag in pdf_tags:
    href = tag["href"]
    title = tag.get("title", "").lower()
    if not href.endswith(".pdf"):
        continue

    if "fund letter" in title and "2024" in title and "year-end" in title:
        pdf_links["Shareholder_Letter"] = href
    elif "tailored shareholder report" in title and "2024" in title and "dec" in title:
        pdf_links["Tailored_Report"] = href
    elif "annual report" in title and "2024" in title and "dec" in title:
        pdf_links["Annual_Report"] = href

# Download all PDFs
pdf_paths = []
for label, pdf_url in pdf_links.items():
    try:
        file_name = f"Sequoia_{label}_{today}.pdf"
        path = os.path.join(downloads_dir, file_name)
        pdf_response = scraper.get(pdf_url, timeout=30)
        with open(path, "wb") as f:
            f.write(pdf_response.content)
        print(f"Downloaded: {file_name}")
        pdf_paths.append(path)
    except Exception as e:
        print(f"Error downloading {label}: {e}")

# Merge PDFs if there are multiple
if len(pdf_paths) > 1:
    merger = PdfMerger()
    for path in pdf_paths:
        merger.append(path)
    merged_name = f"Sequoia_{today}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"Merged {len(pdf_paths)} PDFs -> {merged_name}")

print(f"Downloaded {len(pdf_paths)} Sequoia report(s).")
