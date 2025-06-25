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

# Load LayoutLMv3 Model
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")

def pdf_to_images(pdf_path, dpi=300):
    poppler_path = r"C:\poppler-24.08.0\Library\bin" 
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    return images

def extract_text_with_ai(image):
    """Extract text from an image using OCR and AI-powered LayoutLMv3"""
    extracted_text = pytesseract.image_to_string(image)
    return extracted_text.strip()

""" def extract_full_text_from_pdf(pdf_path):
    images = pdf_to_images(pdf_path)
    full_text = ""
    for img in images:
        full_text += extract_text_with_ai(img) + "\n\n"
    return full_text
 """

def extract_full_text_from_pdf(pdf_path):
    images = pdf_to_images(pdf_path)
    print(f"Starting parallel OCR on {len(images)} pages...")
    
    def ocr_page(img):
        return extract_text_with_ai(img)

    with ThreadPoolExecutor() as executor:
        texts = list(executor.map(ocr_page, images))

    return "\n\n".join(texts)

""" def is_holdings_paragraph(paragraph, tickers_dict):
    # Skip long paragraphs with lots of symbols/numbers and multiple company mentions
    if len(paragraph) > 600:
        symbol_chars = ['.', '%', '$', '-', '+', '=', '|']
        symbol_ratio = sum(paragraph.count(ch) for ch in symbol_chars) / max(len(paragraph), 1)
        if symbol_ratio > 0.04:
            company_mentions = sum(1 for name in tickers_dict.values() if name.lower() in paragraph.lower())
            if company_mentions >= 3:
                return True
    return False """

def is_holdings_paragraph(paragraph, tickers_dict):
    if len(paragraph) < 400:
        return False
    # Count company mentions
    company_mentions = sum(1 for name in tickers_dict.values() if re.search(rf'\b{re.escape(name)}\b', paragraph))
    # Count $ signs
    dollar_signs = paragraph.count('$')
    # Count financial noise patterns like Inc., Ltd., Corp., Cl A, ADR, etc.
    financial_terms = len(re.findall(r'\b(Inc\.|Ltd\.|Corp\.|Cl [A-Z]|ADR|Holdings|Technologies|LLC|S\.A\.|PLC)\b', paragraph))
    # Count visual separators
    symbol_chars = ['.', '%', '$', '-', '+', '=', '|']
    symbol_ratio = sum(paragraph.count(ch) for ch in symbol_chars) / max(len(paragraph), 1)
    if (
        company_mentions >= 3 and
        (dollar_signs >= 5 or financial_terms >= 5 or symbol_ratio > 0.04)
    ):
        return True
    return False


def filter_relevant_paragraphs(paragraphs, tickers_dict):
    """Filter paragraphs that mention Spotify AND contain investment-related context."""
    keywords = ["performance", "returns", "growth", "valuation", "strategy", 
                "fund", "impact", "investment", "revenue", "market", "expansion", 
                "company", "subscribers", "profit", "financials", "earnings", "business"]

    relevant_paragraphs = []
    
    for paragraph in paragraphs:
        words = paragraph.split()

        # Rule 0: Remove paragraphs that start with "Table" (case-insensitive)
        if paragraph.strip().lower().startswith("table"):
            continue

        # Rule 1: Paragraphs that are mostly numeric — remove if more than 40% of tokens are numbers
        num_count = sum(
            1 for word in words
            if any(char.isdigit() for char in word.strip(string.punctuation))
        )
        if len(words) > 0 and (num_count / len(words)) > 0.4:
            continue

        # **Rule 2: Remove paragraphs that are mostly numbers (e.g., stock tables)**
        if re.match(r"^\s*[\d\s.,%$-]+\s*$", paragraph):
            continue  # Skip paragraphs that are only numbers

         # Rule 3: Skip paragraphs with lots of symbols/visual separators (common in holdings dumps)
        symbol_chars = ['.', '%', '$', '-', '+', '=', '|']
        symbol_ratio = sum(paragraph.count(ch) for ch in symbol_chars) / max(len(paragraph), 1)
        if symbol_ratio > 0.04:  # ~4% symbol ratio threshold
            continue

        # Rule 4: Skip paragraphs with excessive uppercase (common in security names)
        uppercase_ratio = sum(1 for ch in paragraph if ch.isupper()) / max(len(paragraph), 1)
        if uppercase_ratio > 0.35:
            continue

        # **Rule 5: Keep only longer paragraphs (20+ words)**
        if len(words) < 20:
            continue

        # **Rule 6: Removing potential dumps**    
        if is_holdings_paragraph(paragraph, tickers_dict):
            continue

        # **Rule 7: Paragraph must contain investment-related keywords**
        if any(keyword in paragraph.lower() for keyword in keywords):
            relevant_paragraphs.append(paragraph)

    return relevant_paragraphs

def identify_companies_in_text(text):
    found = {}
    for ticker, company in tickers.items():
        if ticker in text or company.lower() in text.lower():
            found[ticker] = company
    return found

def extract_company_paragraphs(text, company_name):
    paragraphs = text.split("\n\n")
    relevant_paragraphs = []
    pattern = re.compile(rf'\b{re.escape(company_name)}\b', re.IGNORECASE)
    
    for para in paragraphs:
        if pattern.search(para):
            relevant_paragraphs.append(para.strip())
    return relevant_paragraphs

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

def save_results_to_pdf(results, output_path):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    margin = 50
    y = height - margin
    line_height = 14

    c.setFont("Helvetica", 12)
    for company, paragraphs in results.items():
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, f"{company}")
        y -= line_height

        c.setFont("Helvetica", 12)
        for i, para in enumerate(paragraphs, 1):
            para_lines = textwrap.wrap(f"Paragraph {i}: {para}", width=100)
            for line in para_lines:
                if y <= margin:
                    c.showPage()
                    y = height - margin
                    c.setFont("Helvetica", 12)
                c.drawString(margin, y, line)
                y -= line_height
            y -= line_height  # extra space after each paragraph

        y -= line_height  # space between companies

        if y <= margin:
            c.showPage()
            y = height - margin

    c.save()

def main(pdf_path):
    full_text = extract_full_text_from_pdf(pdf_path)
    detected_companies = identify_companies_in_text(full_text)

    results = {}
    for ticker, company_name in detected_companies.items():
        raw_paragraphs = extract_company_paragraphs(full_text, company_name)
        filtered = filter_relevant_paragraphs(raw_paragraphs, tickers)
        if filtered:
            results[company_name] = filtered
    # Deduplicate across all company paragraphs after all processing
    results = remove_duplicate_paragraphs(results)
    return results

if __name__ == "__main__":
    print("This file is meant to be imported by excerpt.py — not run directly.")
