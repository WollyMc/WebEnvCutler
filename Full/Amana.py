import asyncio
import os
from pathlib import Path
from PyPDF2 import PdfMerger
from playwright.async_api import async_playwright

BASE_URL = "https://www.saturna.com/insights/market-commentaries"
DOWNLOAD_DIR = Path("downloads/amana")
NUM_ARTICLES = 3

async def download_pdf_from_article(page, url, index):
    try:
        await page.goto(url)
        print(f"→ Opened article {index + 1}: {url}")
        await page.wait_for_selector("div.download-link a[href$='.pdf']", timeout=10000)
        link = await page.get_attribute("div.download-link a[href$='.pdf']", "href")

        if link:
            pdf_url = f"https://www.saturna.com{link}" if link.startswith("/") else link
            pdf_name = f"Amana_Article_{index+1}.pdf"
            pdf_path = DOWNLOAD_DIR / pdf_name
            print(f"  Downloading: {pdf_url}")
            async with page.context.expect_download() as download_info:
                await page.evaluate(f"""() => window.open("{pdf_url}", "_blank")""")
            download = await download_info.value
            await download.save_as(str(pdf_path))
            print(f"   Saved to: {pdf_path}")
            return pdf_path
        else:
            print("   No PDF link found.")
            return None
    except Exception as e:
        print(f"   Error processing article {index + 1}: {e}")
        return None

async def run():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    pdf_paths = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("Opening main commentary page...")
        await page.goto(BASE_URL, timeout=60000)
        await page.wait_for_selector("article.node--type-insight a", timeout=20000)

        anchors = await page.query_selector_all("article.node--type-insight a")
        links = []
        seen = set()
        for a in anchors:
            href = await a.get_attribute("href")
            if href and "/insights/market-commentaries/" in href and href not in seen:
                links.append("https://www.saturna.com" + href)
                seen.add(href)
                if len(links) == NUM_ARTICLES:
                    break

        print(f"\n Found {len(links)} articles\n")
        for i, link in enumerate(links):
            pdf = await download_pdf_from_article(page, link, i)
            if pdf:
                pdf_paths.append(pdf)

        await browser.close()

    if pdf_paths:
        merger = PdfMerger()
        for path in pdf_paths:
            merger.append(str(path))
        output_path = DOWNLOAD_DIR / "Amana_Commentaries_Merged.pdf"
        merger.write(str(output_path))
        merger.close()
        print(f"\n Merged PDF saved to: {output_path}")
    else:
        print("\n No PDFs to merge.")

if __name__ == "__main__":
    asyncio.run(run())
