import os
import time
import random
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger
from datetime import datetime

# Path to your manually downloaded ChromeDriver
driver_path = r"C:\chromedriver-win64\chromedriver.exe"

# Fidelity document URLs & their date elements
document_info = {
    "Quarterly Fund Review": {
        "url": "https://fundresearch.fidelity.com/mutual-funds/analysis/316345305?documentType=QFR",
        "date_id": "shcomm-QuarterlyFundReviewDate"
    },
    "Portfolio Manager Q&A": {
        "url": "https://fundresearch.fidelity.com/mutual-funds/analysis/316345305?documentType=QAA",
        "date_id": "shcomm-PortfolioManagersQuestionAnswerDate"
    },
    "Chairman’s Message": {
        "url": "https://fundresearch.fidelity.com/mutual-funds/analysis/316345305?documentType=CHM",
        "date_id": "shcomm-ChairmanMessageDate"
    }
}

# Configure Chrome WebDriver
options = Options()
options.add_argument("--headless")  
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-blink-features=AutomationControlled")  
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
options.add_argument("--disable-web-security")
options.add_argument("--ignore-certificate-errors")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")

# Function to initialize WebDriver
def get_webdriver():
    return webdriver.Chrome(service=Service(driver_path), options=options)

# Dictionary to store extracted PDF links and dates
pdf_links = {}
pdf_dates = {}

# Extract PDF links and dates using Selenium
for doc_name, info in document_info.items():
    url = info["url"]
    date_id = info["date_id"]
    
    print(f"Fetching: {doc_name} ({url})")

    retries = 5  
    timeout = 15  

    for attempt in range(retries):
        try:
            driver = get_webdriver()
            driver.get(url)
            
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(3, 5))  

            # Extract PDF link
            pdf_element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/bin-public/') and contains(text(), 'View as PDF')]"))
            )
            pdf_link = pdf_element.get_attribute("href")

            if pdf_link and pdf_link.startswith("https://www.fidelity.com/bin-public/"):
                pdf_links[doc_name] = pdf_link
                print(f"Extracted PDF link: {pdf_link}")
            else:
                print(f"Could not find valid PDF for {doc_name}")

            # Extract date
            try:
                date_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, date_id))
                )
                raw_date = date_element.text.strip()
                parsed_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%m%d%y")
                pdf_dates[doc_name] = parsed_date
                print(f"Extracted Date: {raw_date} → {parsed_date}")
            except:
                print(f"Could not extract date for {doc_name}, using 'UnknownDate'")
                pdf_dates[doc_name] = "UnknownDate"

            driver.quit()  
            break  

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {doc_name}: {e}")
            timeout += 5  
            time.sleep(random.uniform(5, 10))  
            driver.quit()  

            if "ERR_CONNECTION_RESET" in str(e):
                print("Connection reset detected. Trying again with a fresh session.")
                time.sleep(random.uniform(10, 15))  

            if attempt == retries - 1:
                print(f"Failed after {retries} attempts.")

# If missing any required PDF, exit
if len(pdf_links) < 3:
    print("Error: Not all required PDFs were found. Exiting.")
    exit()

# Define file names using extracted dates
pdf_names = {
    doc_name: f"Fidelity_{pdf_dates[doc_name]}_{doc_name.replace(' ', '_')}.pdf"
    for doc_name in pdf_links
}
merged_pdf_name = f"Fidelity_{pdf_dates['Quarterly Fund Review']}_Merged.pdf"

# Create directory structure
main_dir = "Fidelity"
main_dir = os.path.join("Cutler", "Fidelity")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)

# Delete old reports before downloading the latest one
for file in os.listdir(downloads_dir):
    file_path = os.path.join(downloads_dir, file)
    if os.path.isfile(file_path) and file.endswith(".pdf"):
        os.remove(file_path)
        print(f"Deleted old report: {file}")

# Download all three PDFs
pdf_paths = []
for doc_name, pdf_url in pdf_links.items():
    pdf_path = os.path.join(downloads_dir, pdf_names[doc_name])
    try:
        response = requests.get(pdf_url, timeout=30)
        with open(pdf_path, "wb") as file:
            file.write(response.content)
        pdf_paths.append(pdf_path)
        print(f"Downloaded: {pdf_names[doc_name]}")
    except requests.exceptions.Timeout:
        print(f"Failed to download {pdf_names[doc_name]} due to timeout.")
    except Exception as e:
        print(f"Error downloading {pdf_names[doc_name]}: {e}")

# Merge all PDFs into one
if pdf_paths:
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)

    merged_path = os.path.join(downloads_dir, merged_pdf_name)
    merger.write(merged_path)
    merger.close()
    print(f"Merged PDF saved as: {merged_pdf_name}")
else:
    print("No PDFs downloaded. Merging skipped.")
