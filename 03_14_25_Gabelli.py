import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

def get_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)

def main():
    base_url = "https://www.gabelli.com/corporate/investor_relations"
    driver = get_webdriver()
    driver.get(base_url)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
    time.sleep(3)

    links = driver.find_elements(By.XPATH, "//a[span[contains(text(),'Quarterly Report') or contains(text(),'Annual Report')]]")

    latest_report_url = None
    latest_report_type = None

    if links:
        latest_link = links[0]
        latest_report_url = latest_link.get_attribute("href")
        latest_report_type = latest_link.text.strip().replace(" ", "_")
    else:
        print("No financial reports found.")
        driver.quit()
        return

    today = datetime.today().strftime("%Y%m%d")
    pdf_name = f"Gabelli_{today}_{latest_report_type}.pdf"

    main_dir = os.path.join("Cutler", "Gabelli")
    downloads_dir = os.path.join(main_dir, "downloads")
    excerpted_dir = os.path.join(main_dir, "excerpted")

    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(excerpted_dir, exist_ok=True)

    for file in os.listdir(downloads_dir):
        file_path = os.path.join(downloads_dir, file)
        if os.path.isfile(file_path) and file.endswith(".pdf"):
            os.remove(file_path)
            print(f"Deleted old report: {file}")

    pdf_path = os.path.join(downloads_dir, pdf_name)
    try:
        response = requests.get(latest_report_url)
        with open(pdf_path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {pdf_name}")
    except Exception as e:
        print(f"Error downloading report: {e}")

    driver.quit()
    print("Process completed.")

if __name__ == "__main__":
    main()
