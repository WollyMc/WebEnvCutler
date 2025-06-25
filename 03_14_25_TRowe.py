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

# Path to your ChromeDriver
driver_path = r"C:\chromedriver-win64\chromedriver.exe"

# T. Rowe Price document URLs & their corresponding identifiers
document_info = {
    "Quarterly Fund Review": {
        "url": "https://www.troweprice.com/personal-investing/funds/mutual-funds/prospectuses-reports.html",
        "pdf_xpath": "//a[contains(@href, '.pdf') and contains(text(), 'Quarterly Review')]",
        "date_xpath": "//span[contains(text(), 'Quarterly Review')]/following-sibling::span"
    },
    "Global Markets Quarterly Update": {
        "url": "https://www.troweprice.com/personal-investing/resources/insights/global-markets-quarterly-update.html",
        "pdf_xpath": "//a[contains(@href, '.pdf') and contains(text(), 'Download the PDF')]",
        "date_xpath": "//time"
    }
}

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

# Dictionary to store extracted PDF links and dates
pdf_links = {}
pdf_dates = {}

# Extract PDF links and dates using Selenium
for doc_name, info in document_info.items():
    url = info["url"]
    pdf_xpath = info["pdf_xpath"]
    date_xpath = info["date_xpath"]

    print(f"Fetching: {doc_name} ({url})")

    retries = 5
    timeout = 15

    for attempt in range(retries):
        try:
            driver = get_webdriver()
            driver.get(url)

            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(random.uniform(3, 6))  # Add extra wait for JavaScript content

            # Extract PDF link
            try:
                pdf_element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, pdf_xpath))
                )
                pdf_link = pdf_element.get_attribute("href")
            except:
                print(f"Could not find PDF for {doc_name}. Retrying with new strategy.")
                pdf_link = None

            if pdf_link and pdf_link.startswith("/"):
                pdf_link = "https://www.troweprice.com" + pdf_link

            if pdf_link:
                pdf_links[doc_name] = pdf_link
                print(f"Extracted PDF link: {pdf_link}")
            else:
                print(f"No valid PDF found for {doc_name}")

            # Extract date
            try:
                date_element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, date_xpath))
                )
                raw_date = date_element.text.strip()
                parsed_date = datetime.strptime(
                    raw_date, "%B %d, %Y"
                ).strftime("%Y%m%d")
                pdf_dates[doc_name] = parsed_date
                print(f"Extracted Date: {raw_date} → {parsed_date}")
            except Exception as e:
                print(f"Could not extract date for {doc_name}, using 'UnknownDate': {e}")
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

# Extract Quarterly Fund Fact Sheets for U.S. Stock Funds
fund_url = "https://www.troweprice.com/personal-investing/funds/mutual-funds/prospectuses-reports.html"
print("Fetching U.S. Stock Fund Fact Sheets...")

driver = get_webdriver()
driver.get(fund_url)

WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)

soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

fund_sections = soup.find_all("a", href=True)

fact_sheets = {}

for link in fund_sections:
    href = link["href"]
    if "quarterly-factsheet" in href and href.endswith(".pdf"):
        fund_name = link.get_text(strip=True).replace("ViewPDF", "").strip()
        pdf_url = f"https://www.troweprice.com{href}"
        fact_sheets[fund_name] = pdf_url

# If no PDFs were found, exit
if not pdf_links and not fact_sheets:
    print("Error: No PDFs were found. Exiting.")
    exit()

# Define file names using extracted dates
pdf_names = {
    doc_name: f"TRowePrice_{pdf_dates[doc_name]}_{doc_name.replace(' ', '_')}.pdf"
    for doc_name in pdf_links
}

merged_pdf_name = f"TRowePrice_{pdf_dates.get('Quarterly Fund Review', 'UnknownDate')}_Merged.pdf"

# Create directory structure
main_dir = os.path.join("Cutler", "T_Rowe_Price")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")

os.makedirs(downloads_dir, exist_ok=True)

# Delete old reports before downloading the latest ones
for file in os.listdir(downloads_dir):
    file_path = os.path.join(downloads_dir, file)
    if os.path.isfile(file_path) and file.endswith(".pdf"):
        os.remove(file_path)
        print(f"Deleted old report: {file}")

# Download all Quarterly Fund Fact Sheets
for fund_name, pdf_url in fact_sheets.items():
    pdf_path = os.path.join(downloads_dir, f"{fund_name}_Quarterly_Fund_Fact_Sheet.pdf")
    try:
        response = requests.get(pdf_url, timeout=30)
        with open(pdf_path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {fund_name} Quarterly Fund Fact Sheet")
    except requests.exceptions.Timeout:
        print(f"Failed to download {fund_name} Quarterly Fund Fact Sheet due to timeout.")
    except Exception as e:
        print(f"Error downloading {fund_name} Quarterly Fund Fact Sheet: {e}")

# Download all other extracted PDFs
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

print("All reports downloaded successfully.")
