import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError

# === Paths ===
DOWNLOAD_DIR = os.path.join("Cutler", "ALPS", "downloads")
MERGED_PDF = os.path.join(DOWNLOAD_DIR, "ALPS_Merged.pdf")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# === Fetch HTML ===
url = "https://www.alpsfunds.com/document-library?doc_category=Literature&doc_type=Commentary"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# === Extract commentary PDF links ===
commentary_links = []
for td in soup.find_all("td", class_="download"):
    a = td.find("a", href=True)
    if a and a["href"].endswith(".pdf") and "comm" in a["href"]:
        full_url = urljoin(url, a["href"])
        commentary_links.append(full_url)

print(f" Found {len(commentary_links)} commentary PDFs.")

# === Download PDFs ===
downloaded_files = []
for idx, link in enumerate(commentary_links, 1):
    try:
        res = requests.get(link)
        if not res.content.startswith(b"%PDF"):
            print(f"  Invalid PDF at: {link}")
            continue
        file_name = f"{idx:02d}_ALPS_Commentary.pdf"
        path = os.path.join(DOWNLOAD_DIR, file_name)
        with open(path, "wb") as f:
            f.write(res.content)
        print(f"  Downloaded: {file_name}")
        downloaded_files.append(path)
    except Exception as e:
        print(f"  Failed to download {link}: {e}")

# === Merge Valid PDFs ===
valid_files = []
if downloaded_files:
    merger = PdfMerger()
    for file in downloaded_files:
        try:
            PdfReader(file)  # Try to open it
            merger.append(file)
            valid_files.append(file)
        except PdfReadError:
            print(f"  Skipped corrupted PDF: {file}")
            os.remove(file)
        except Exception as e:
            print(f"  Error with {file}: {e}")
    if valid_files:
        merger.write(MERGED_PDF)
        merger.close()
        print(f"\n Merged PDF saved at: {MERGED_PDF}")
    else:
        print(" All PDFs were invalid. Nothing merged.")
else:
    print(" No valid PDFs to download.")
