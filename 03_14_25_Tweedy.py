import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger

# === Setup Paths ===
URL = "https://www.tweedyfunds.com/commentary/"
BASE_URL = "https://www.tweedyfunds.com"
today_str = datetime.today().strftime('%Y%m%d')

script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Tweedy")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Clear old downloads
for f in os.listdir(downloads_dir):
    if f.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, f))

# === Step 1: Fetch and Parse Page ===
print("Fetching Tweedy Funds commentary page...")
response = requests.get(URL)
soup = BeautifulSoup(response.text, "html.parser")

# === Step 2: Find latest commentary link ===
pdf_link = None
for a_tag in soup.select("a[href$='.pdf']"):
    href = a_tag.get("href")
    if "FundCommentary" in href:
        pdf_link = href if href.startswith("http") else BASE_URL + href
        break

if not pdf_link:
    print("No FundCommentary PDF found on the page.")
    exit(1)

print(f"Found PDF: {pdf_link}")

# === Step 3: Download the PDF ===
filename = pdf_link.split("/")[-1]
filepath = os.path.join(downloads_dir, filename)

try:
    pdf_resp = requests.get(pdf_link, timeout=30)
    if pdf_resp.ok and pdf_resp.headers.get("Content-Type", "").lower().startswith("application/pdf"):
        with open(filepath, "wb") as f:
            f.write(pdf_resp.content)
        print(f"Saved: {filename}")
    else:
        print("Failed to download a valid PDF.")
        exit(1)
except Exception as e:
    print(f"Error downloading PDF: {e}")
    exit(1)

# === Step 4: Merge (even if single) ===
merger = PdfMerger()
merger.append(filepath)
merged_name = f"Tweedy_{today_str}_Merged.pdf"
merged_path = os.path.join(downloads_dir, merged_name)
merger.write(merged_path)
merger.close()
print(f"Merged PDF saved as: {merged_name}")
