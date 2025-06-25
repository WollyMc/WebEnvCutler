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

# Path to your manually downloaded ChromeDriver
driver_path = r"C:\chromedriver-win64\chromedriver.exe"

# ACI Quarterly Performance Update URL
document_info = {
    "Quarterly Performance Update": {
        "url": "https://www.americancentury.com/insights/quarterly-performance-update/",
        "date_xpath": "//div[contains(@class, 'pub-date')]"  # Adjusted for ACI's date structure
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
    date_xpath = info["date_xpath"]

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
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.pdf')]"))
            )
            pdf_link = pdf_element.get_attribute("href")

            if pdf_link:
                pdf_links[doc_name] = pdf_link
                print(f"Extracted PDF link: {pdf_link}")
            else:
                print(f"Could not find valid PDF for {doc_name}")

            # Extract date
            try:
                date_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, date_xpath))
                )
                raw_date = date_element.text.strip()
                parsed_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y%m%d")
                pdf_dates[doc_name] = parsed_date
                print(f"📅 Extracted Date: {raw_date} → {parsed_date}")
            except Exception as e:
                print(f"Could not extract date for {doc_name}, using fallback method.")
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

# If missing the required PDF, exit
if not pdf_links:
    print("Error: Required PDF was not found. Exiting.")
    exit()

# Define file names using extracted dates
pdf_name = f"ACI_{pdf_dates['Quarterly Performance Update']}_Quarterly_Performance_Update.pdf"

# Create directory structure
main_dir = os.path.join("Cutler", "American_Century_Investments")
downloads_dir = os.path.join(main_dir, "downloads")
excerpted_dir = os.path.join(main_dir, "excerpted")
os.makedirs(downloads_dir, exist_ok=True)

# Delete old reports before downloading the latest one
for file in os.listdir(downloads_dir):
    file_path = os.path.join(downloads_dir, file)
    if os.path.isfile(file_path) and file.endswith(".pdf"):
        os.remove(file_path)
        print(f"Deleted old report: {file}")

# Download the PDF
pdf_path = os.path.join(downloads_dir, pdf_name)
try:
    response = requests.get(pdf_links["Quarterly Performance Update"], timeout=30)
    with open(pdf_path, "wb") as file:
        file.write(response.content)
    print(f"Downloaded: {pdf_name}")
except requests.exceptions.Timeout:
    print(f"Failed to download {pdf_name} due to timeout.")
except Exception as e:
    print(f"Error downloading {pdf_name}: {e}")
