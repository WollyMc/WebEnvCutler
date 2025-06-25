from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, requests
from PyPDF2 import PdfMerger

# Setup Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(service=Service(), options=options)

# Go to Harbor Capital Fund Documents page
driver.get("https://www.harborcapital.com/documents/fund/")

# Wait for buttons to load
WebDriverWait(driver, 30).until(
    EC.presence_of_all_elements_located((By.XPATH, "//button[contains(., 'Quarterly Report')]"))
)

# Extract all buttons containing 'Quarterly Report'
buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Quarterly Report')]")

pdf_links = []
for btn in buttons:
    data_doc = btn.get_attribute("data-doc")
    if data_doc and data_doc.endswith(".pdf"):
        full_url = f"https://www.harborcapital.com{data_doc}"
        pdf_links.append(full_url)

driver.quit()

# Directory setup
main_dir = os.path.join("Cutler", "Harbor")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

# Cleanup old files
for file in os.listdir(downloads_dir):
    if file.endswith(".pdf"):
        os.remove(os.path.join(downloads_dir, file))

# Download PDFs
for i, link in enumerate(pdf_links):
    filename = f"Harbor_QR_{i+1}.pdf"
    path = os.path.join(downloads_dir, filename)
    response = requests.get(link)
    with open(path, "wb") as f:
        f.write(response.content)
    print(f"Downloaded: {filename}")

# Merge downloaded PDFs
merged_pdf_name = "HarborFunds_Merged.pdf"
merged_path = os.path.join(downloads_dir, merged_pdf_name)

pdf_files = [os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir) if f.endswith(".pdf") and f != merged_pdf_name]

if pdf_files:
    merger = PdfMerger()
    for pdf in sorted(pdf_files):  # Optional: sort alphabetically
        merger.append(pdf)
    merger.write(merged_path)
    merger.close()
    print(f"Merged PDF saved as: {merged_pdf_name}")
else:
    print("No PDFs found to merge.")

