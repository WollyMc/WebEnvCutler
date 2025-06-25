import os
import time
import shutil
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PyPDF2 import PdfMerger, PdfReader
from PyPDF2.errors import PdfReadError
from webdriver_manager.chrome import ChromeDriverManager

# === Config ===
MAIN_DIR = os.path.join("Cutler", "AXA")
DOWNLOAD_DIR = os.path.join(MAIN_DIR, "downloads")
TEMP_CHROME_DOWNLOAD_DIR = os.path.join(MAIN_DIR, "chrome_temp")
MERGED_PDF = os.path.join(DOWNLOAD_DIR, "AXA_Merged.pdf")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_CHROME_DOWNLOAD_DIR, exist_ok=True)

# === Date Filter ===
today = datetime.today()
current_month = today.strftime("%m")
current_year = today.strftime("%Y")

# === Clean chrome_temp ===
for f in os.listdir(TEMP_CHROME_DOWNLOAD_DIR):
    try:
        os.remove(os.path.join(TEMP_CHROME_DOWNLOAD_DIR, f))
    except:
        pass

# === Setup Selenium with WebDriver Manager ===
chrome_options = Options()
prefs = {
    "download.default_directory": os.path.abspath(TEMP_CHROME_DOWNLOAD_DIR),
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 20)

driver.get("https://erie.equitableadvisors.com/market-watch-c217c")
time.sleep(5)

# === Find all date spans ===
date_spans = driver.find_elements(By.CSS_SELECTOR, "span.date")
print(f" Found {len(date_spans)} potential articles by date.")

downloaded_files = []

for idx, date_span in enumerate(date_spans, start=1):
    try:
        date_str = date_span.text.strip()
        pub_date = datetime.strptime(date_str, "%m/%d/%Y")
    except:
        continue

    if pub_date.strftime("%m") == current_month and pub_date.strftime("%Y") == current_year:
        try:
            article_div = date_span.find_element(By.XPATH, "./ancestor::div[2]")
            read_button = article_div.find_element(By.XPATH, ".//button[contains(text(), 'Click to read')]")
            driver.execute_script("arguments[0].click();", read_button)

            # Wait for modal and click proceed
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.disclaimerProceed")))
            proceed = driver.find_element(By.CSS_SELECTOR, "a.disclaimerProceed")
            proceed.click()

            # === Wait for download to complete ===
            download_complete = False
            wait_time = 0
            while not download_complete and wait_time < 20:
                time.sleep(1)
                crdownload_files = glob.glob(os.path.join(TEMP_CHROME_DOWNLOAD_DIR, "*.crdownload"))
                pdf_files = glob.glob(os.path.join(TEMP_CHROME_DOWNLOAD_DIR, "*.pdf"))
                if not crdownload_files and pdf_files:
                    download_complete = True
                wait_time += 1

            if not download_complete:
                print(f" Download timed out for article {date_str}")
                continue

            # Get the downloaded PDF
            latest_pdf = max(glob.glob(os.path.join(TEMP_CHROME_DOWNLOAD_DIR, "*.pdf")), key=os.path.getctime)
            target_name = f"{pub_date.strftime('%Y-%m-%d')}_{idx}.pdf"
            final_path = os.path.join(DOWNLOAD_DIR, target_name)
            shutil.move(latest_pdf, final_path)
            print(f" Downloaded via browser: {target_name}")
            downloaded_files.append(final_path)

            # Close modal
            close_btn = driver.find_element(By.CSS_SELECTOR, "button.fancybox-close-small")
            close_btn.click()
            time.sleep(1)

        except Exception as e:
            print(f" Error on article dated {date_str}: {e}")

driver.quit()

# === Merge valid PDFs ===
valid_files = []
if downloaded_files:
    merger = PdfMerger()
    for f in downloaded_files:
        try:
            PdfReader(f)  # Validation
            merger.append(f)
            valid_files.append(f)
        except PdfReadError:
            print(f" Skipped corrupted PDF: {f}")
            os.remove(f)
        except Exception as e:
            print(f" Error appending {f}: {e}")
    if valid_files:
        merger.write(MERGED_PDF)
        merger.close()
        print(f"\n Merged PDF saved at: {MERGED_PDF}")
    else:
        print(" All downloaded PDFs were invalid. Nothing merged.")
else:
    print(" No PDFs downloaded.")
