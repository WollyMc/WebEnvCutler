import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# === Setup Directories ===
today_str = datetime.today().strftime('%Y%m%d')
script_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.join(script_dir, "Cutler", "Tortoise")
downloads_dir = os.path.join(main_dir, "downloads")
os.makedirs(downloads_dir, exist_ok=True)

BASE_URL = "https://oef.tortoisecapital.com"
FUND_URL = f"{BASE_URL}/funds/tortoise-energy-infrastructure-total-return-fund-inst/"

latest_pdfs = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    try:
        print("[Tortoise] Visiting fund page...")
        page.goto(FUND_URL, timeout=60000)
        page.wait_for_timeout(3000)
        soup = BeautifulSoup(page.content(), "html.parser")

        # Locate Quarterly Commentary link and extract the viewer page URL
        for li in soup.select("li.widget_bar__resources-list__item"):
            a_tag = li.find("a")
            if a_tag and "quarterly commentary" in a_tag.text.strip().lower():
                viewer_path = a_tag["href"]
                viewer_url = urljoin(BASE_URL, viewer_path)
                print(f"[Tortoise] Visiting viewer page: {viewer_url}")

                page.goto(viewer_url, timeout=30000)
                page.wait_for_timeout(3000)

                try:
                    iframe = page.query_selector("iframe")
                    if iframe:
                        real_pdf_url = iframe.get_attribute("src")
                        full_pdf_url = urljoin(BASE_URL, real_pdf_url)
                        print(f"[Tortoise] Triggering download from iframe: {full_pdf_url}")

                        with page.expect_download(timeout=15000) as download_info:
                            page.goto(full_pdf_url)
                        download = download_info.value
                        save_path = os.path.join(downloads_dir, "Tortoise Quarterly Commentary - commentary.pdf")
                        download.save_as(save_path)
                        print(f"[Tortoise] Downloaded: {save_path}")
                        latest_pdfs.append(save_path)
                    else:
                        print("[Tortoise] iframe not found in viewer page.")
                except Exception as e:
                    print(f"[Tortoise] Error during download: {e}")
                break

    except PlaywrightTimeout:
        print("[Tortoise] Timeout visiting fund page.")
    except Exception as e:
        print(f"[Tortoise] Error during scraping: {e}")
    finally:
        browser.close()

# === Merge PDFs ===
if latest_pdfs:
    merger = PdfMerger()
    for pdf in latest_pdfs:
        try:
            merger.append(pdf)
        except Exception as e:
            print(f"[Tortoise] Skipped corrupt PDF during merge: {e}")
    merged_name = f"Tortoise_{today_str}_Merged.pdf"
    merged_path = os.path.join(downloads_dir, merged_name)
    merger.write(merged_path)
    merger.close()
    print(f"\nMerged {len(latest_pdfs)} PDFs into {merged_name}")
else:
    print("No Tortoise PDFs downloaded.")
