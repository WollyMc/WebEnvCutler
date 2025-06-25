import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from PyPDF2 import PdfMerger
from bs4 import BeautifulSoup

# Path to ChromeDriver
driver_path = r"C:\chromedriver-win64\chromedriver.exe"

# URL for Poplar Forest Funds Quarterly Reports
poplar_reports_url = "https://poplarforestfunds.com/category/quarterly-reports/"

# Configure Chrome WebDriver
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--enable-unsafe-swiftshader")  # Fix for WebGL issue
options.add_argument("--log-level=3")
options.add_argument("--disable-web-security")
options.add_argument("--ignore-certificate-errors")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
)

# Function to initialize WebDriver
def get_webdriver():
    return webdriver.Chrome(service=Service(driver_path), options=options)

# Step 1: Get the latest 4 quarterly report links
print("\nFetching Poplar Forest Funds Quarterly Reports...")

driver = get_webdriver()
driver.get(poplar_reports_url)

WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)

soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

# Extract the latest 4 quarterly report links
report_links = []
for link in soup.find_all("h2", class_="entry-title"):
    a_tag = link.find("a")
    if a_tag and a_tag["href"].startswith("https://poplarforestfunds.com/"):
        report_links.append(a_tag["href"])

# Keep only the latest 4 reports
report_links = report_links[:4]
print(f" Found {len(report_links)} latest reports.")

# If no reports were found, exit
if not report_links:
    print(" No reports found. Exiting.")
    exit()

# Create directory structure
main_dir = os.path.join("Cutler", "Poplar_Forest_Funds")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)

# Delete old reports before downloading new ones
for file in os.listdir(downloads_dir):
    file_path = os.path.join(downloads_dir, file)
    if os.path.isfile(file_path) and file.endswith(".pdf"):
        os.remove(file_path)
        print(f" Deleted old report: {file}")

# Step 2: Visit each report page and extract the PDF link
pdf_links = {}
for report_url in report_links:
    print(f"\n Fetching report: {report_url}")

    driver = get_webdriver()
    driver.get(report_url)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    report_soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # Extract the PDF download link
    pdf_link = None
    for a_tag in report_soup.find_all("a", href=True):
        if "DOWNLOAD QUARTERLY LETTER" in a_tag.text.upper():
            pdf_link = a_tag["href"]
            break

    if pdf_link:
        pdf_name = pdf_link.split("/")[-1]
        pdf_links[pdf_name] = pdf_link
        print(f" Found PDF: {pdf_name}")
    else:
        print(" No PDF found for this report.")

# Step 3: Download all PDFs
pdf_paths = []
for pdf_name, pdf_url in pdf_links.items():
    pdf_path = os.path.join(downloads_dir, pdf_name)

    try:
        response = requests.get(pdf_url, timeout=30)
        with open(pdf_path, "wb") as file:
            file.write(response.content)
        pdf_paths.append(pdf_path)
        print(f" Downloaded: {pdf_name}")
    except requests.exceptions.Timeout:
        print(f" Failed to download {pdf_name} due to timeout.")
    except Exception as e:
        print(f" Error downloading {pdf_name}: {e}")

# Step 4: Merge all downloaded PDFs into a single file
if pdf_paths:
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)

    merged_pdf_name = f"PoplarForest_{datetime.now().strftime('%Y%m%d')}_Merged.pdf"
    merged_pdf_path = os.path.join(downloads_dir, merged_pdf_name)
    merger.write(merged_pdf_path)
    merger.close()

    print(f"\n Merged PDF saved as: {merged_pdf_name}")
else:
    print("\n No PDFs downloaded. Merging skipped.")

print("\n All reports downloaded and merged successfully.")
