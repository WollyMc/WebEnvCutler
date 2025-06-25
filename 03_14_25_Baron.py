import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure Selenium with Edge
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

# Initialize Edge WebDriver
driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)

# Website URL
base_url = "https://www.baroncapitalgroup.com/insights-webcasts#Reports"
driver.get(base_url)

# Wait for JavaScript to load content
time.sleep(5)

# Extract the page source to find the latest Quarterly Report PDF link
page_source = driver.page_source

# 🔹 Use regex to find the latest Quarterly Report PDF link
pdf_links = re.findall(r'href=["\'](.*?baron-funds-quarterly-report.*?\.pdf)["\']', page_source)

if pdf_links:
    pdf_url = pdf_links[0]  # Get the latest available report
    if pdf_url.startswith("/"):  # Handle relative URLs
        pdf_url = "https://www.baroncapitalgroup.com" + pdf_url

    # 🔹 Extract quarter and year from the PDF filename
    match = re.search(r'quarterly-report-(\d{2})\.(\d{2})\.(\d{4})', pdf_url)
    if match:
        month, day, year = match.groups()
        quarter = "Q4" if month == "12" else f"Q{((int(month) - 1) // 3) + 1}"
        latest_quarter = f"{quarter} {year}"
    else:
        latest_quarter = "Unknown_Quarter"

    pdf_name = f"Baron_{latest_quarter.replace(' ', '_')}.pdf"  # Example: Baron_Q4_2024.pdf

    # Create directory structure
    main_dir = os.path.join("Cutler", "Baron")
    downloads_dir = os.path.join(main_dir, "downloads")
    excerpted_dir = os.path.join(main_dir, "excerpted")

    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(excerpted_dir, exist_ok=True)

    # Delete older reports before downloading the latest one
    for file in os.listdir(downloads_dir):
        file_path = os.path.join(downloads_dir, file)
        if os.path.isfile(file_path) and file.endswith(".pdf"):
            os.remove(file_path)
            print(f"Deleted old report: {file}")

    # 🔹 Download the latest Quarterly Report
    pdf_path = os.path.join(downloads_dir, pdf_name)

    response = requests.get(pdf_url)
    with open(pdf_path, "wb") as file:
        file.write(response.content)

    print(f"Downloaded latest Quarterly Report: {pdf_name}")

else:
    print("No latest Quarterly Report found.")

# Close browser
driver.quit()
print("Process completed.")
