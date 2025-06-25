from pdf2image import convert_from_path
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import pytesseract
import re
import string
from tickers import tickers
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
import os
import textwrap
from concurrent.futures import ThreadPoolExecutor

# Load LayoutLMv3 Model (currently unused, reserved for future enhancement)
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")

# === PDF to Image Conversion ===
def pdf_to_images(pdf_path, dpi=300):
    poppler_path = r"C:\poppler-24.08.0\Library\bin"
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    return images

# === OCR Text Extraction ===
def extract_text_with_ai(image):
    return pytesseract.image_to_string(image).strip()

def extract_full_text_from_pdf(pdf_path):
    images = pdf_to_images(pdf_path)
    print(f"Starting parallel OCR on {len(images)} pages...")

    def ocr_page(img):
        return extract_text_with_ai(img)

    with ThreadPoolExecutor() as executor:
        texts = list(executor.map(ocr_page, images))

    return "\n\n".join(texts)

# === Paragraph Filtering Rules ===
def is_holdings_paragraph(paragraph, tickers_dict):
    if len(paragraph) < 400:
        return False
    company_mentions = sum(1 for name in tickers_dict.values() if re.search(rf'\b{re.escape(name)}\b', paragraph))
    dollar_signs = paragraph.count('$')
    financial_terms = len(re.findall(r'\b(Inc\.|Ltd\.|Corp\.|Cl [A-Z]|ADR|Holdings|Technologies|LLC|S\.A\.|PLC)\b', paragraph))
    symbol_chars = ['.', '%', '$', '-', '+', '=', '|']
    symbol_ratio = sum(paragraph.count(ch) for ch in symbol_chars) / max(len(paragraph), 1)
    
    return company_mentions >= 3 and (dollar_signs >= 5 or financial_terms >= 5 or symbol_ratio > 0.04)

def filter_relevant_paragraphs(paragraphs, tickers_dict):
    keywords = [
        "performance", "returns", "growth", "valuation", "strategy", "fund", "impact",
        "investment", "revenue", "market", "expansion", "company", "subscribers",
        "profit", "financials", "earnings", "business"
    ]

    relevant_paragraphs = []

    for paragraph in paragraphs:
        words = paragraph.split()

        if paragraph.strip().lower().startswith("table"):
            continue
        if len(words) > 0 and (sum(1 for word in words if any(char.isdigit() for char in word.strip(string.punctuation))) / len(words)) > 0.4:
            continue
        if re.match(r"^\s*[\d\s.,%$-]+\s*$", paragraph):
            continue
        symbol_ratio = sum(paragraph.count(ch) for ch in ['.', '%', '$', '-', '+', '=', '|']) / max(len(paragraph), 1)
        if symbol_ratio > 0.04:
            continue
        uppercase_ratio = sum(1 for ch in paragraph if ch.isupper()) / max(len(paragraph), 1)
        if uppercase_ratio > 0.35:
            continue
        if len(words) < 20:
            continue
        if is_holdings_paragraph(paragraph, tickers_dict):
            continue
        if any(keyword in paragraph.lower() for keyword in keywords):
            relevant_paragraphs.append(paragraph)

    return relevant_paragraphs

# === Company Mention Detection ===
def identify_companies_in_text(text):
    found = {}
    for ticker, company in tickers.items():
        if ticker in text or company.lower() in text.lower():
            found[ticker] = company
    return found

def extract_company_paragraphs(text, company_name):
    paragraphs = text.split("\n\n")
    pattern = re.compile(rf'\b{re.escape(company_name)}\b', re.IGNORECASE)
    return [para.strip() for para in paragraphs if pattern.search(para)]

def remove_duplicate_paragraphs(results):
    seen = set()
    deduped_results = {}
    for company, paras in results.items():
        unique_paras = []
        for p in paras:
            if p not in seen:
                seen.add(p)
                unique_paras.append(p)
        if unique_paras:
            deduped_results[company] = unique_paras
    return deduped_results

# === Output PDF Writer ===
def save_results_to_pdf(results, output_path):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    margin = 50
    y = height - margin
    line_height = 14

    for company, paragraphs in results.items():
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, company)
        y -= line_height

        c.setFont("Helvetica", 12)
        for i, para in enumerate(paragraphs, 1):
            lines = textwrap.wrap(f"Paragraph {i}: {para}", width=100)
            for line in lines:
                if y <= margin:
                    c.showPage()
                    y = height - margin
                    c.setFont("Helvetica", 12)
                c.drawString(margin, y, line)
                y -= line_height
            y -= line_height  # Extra space after each paragraph
        y -= line_height  # Space between companies
        if y <= margin:
            c.showPage()
            y = height - margin

    c.save()

# === Orchestration ===
def main(pdf_path):
    full_text = extract_full_text_from_pdf(pdf_path)
    detected_companies = identify_companies_in_text(full_text)

    results = {}
    for ticker, company_name in detected_companies.items():
        raw_paragraphs = extract_company_paragraphs(full_text, company_name)
        filtered = filter_relevant_paragraphs(raw_paragraphs, tickers)
        if filtered:
            results[company_name] = filtered

    return remove_duplicate_paragraphs(results)

if __name__ == "__main__":
    print("This file is meant to be imported by excerpt.py — not run directly.")
