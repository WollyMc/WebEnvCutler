import os
import time
import requests
from PyPDF2 import PdfMerger
from playwright.sync_api import sync_playwright

# === Config ===
FUND_NAME = "Allianz"
BASE_DIR = os.path.join("Cutler", FUND_NAME)
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def fetch_article_links(page):
    page.goto("https://www.allianz.com/en/economic_research/insights/publications.html", timeout=60000)

    for _ in range(10):
        page.mouse.wheel(0, 3000)
        time.sleep(1.5)

    links = page.locator("a.c-heading__link")
    count = links.count()

    article_urls = []
    for i in range(min(count, 6)):
        href = links.nth(i).get_attribute("href")
        if href and href.startswith("/en/economic_research/insights/publications/"):
            article_urls.append(f"https://www.allianz.com{href}")

    return article_urls

def extract_pdf_link(page, url):
    try:
        page.goto(url, timeout=30000)
        time.sleep(5)  # Wait for JS to render the PDF block
        page.wait_for_selector("div.link a[href$='.pdf']", timeout=15000)
        link_element = page.locator("div.link a[href$='.pdf']").first
        href = link_element.get_attribute("href")
        if href:
            return f"https://www.allianz.com{href}"
    except Exception as e:
        print(f" PDF not found on: {url} | {str(e)}")
    return None

def download_pdfs_with_playwright(page, pdf_urls):
    saved_paths = []
    for url in pdf_urls:
        try:
            print(f"Triggering browser download for: {url}")
            with page.expect_download(timeout=15000) as download_info:
                page.evaluate("""url => {
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                }""", url)
            download = download_info.value
            filename = os.path.basename(url.split("?")[0])
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            download.save_as(filepath)
            saved_paths.append(filepath)
            print(f"✓ Downloaded via browser: {filename}")
        except Exception as e:
            print(f"✗ Failed Playwright download for {url}: {e}")
    return saved_paths




def merge_pdfs(paths):
    if not paths:
        print("No PDFs to merge.")
        return
    merged_path = os.path.join(DOWNLOADS_DIR, f"{FUND_NAME}_Latest_6_Merged.pdf")
    merger = PdfMerger()
    valid_paths = []
    for path in paths:
        try:
            with open(path, "rb") as f:
                merger.append(f)
            valid_paths.append(path)
        except Exception as e:
            print(f"✗ Skipped corrupted file {path}: {e}")
    if valid_paths:
        merger.write(merged_path)
        merger.close()
        print(f"Merged PDF created: {merged_path}")
    else:
        print("No valid PDFs to merge.")

# === Main Execution ===
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=250)
    page = browser.new_page()
    print("Opening Allianz insights page...")
    article_urls = fetch_article_links(page)

    pdf_urls = []
    for article_url in article_urls:
        print(f"Checking article: {article_url}")
        pdf_link = extract_pdf_link(page, article_url)
        if pdf_link:
            print(f"✓ PDF found: {pdf_link}")
            pdf_urls.append(pdf_link)
        else:
            print("✗ No PDF found.")

    downloaded_paths = download_pdfs_with_playwright(page, pdf_urls)
    merge_pdfs(downloaded_paths)
    browser.close()
