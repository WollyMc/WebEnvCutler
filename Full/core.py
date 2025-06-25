import os
import subprocess
from datetime import datetime
from PyPDF2 import PdfMerger
from excerption_base import extract_full_text_from_pdf, identify_companies_in_text, extract_company_paragraphs, filter_relevant_paragraphs, remove_duplicate_paragraphs
from tickers import tickers
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
import textwrap
import streamlit as st
import sys
from PyPDF2.errors import PdfReadError
from PyPDF2 import PdfReader

# === Setup Directories ===
base_dir = os.path.join(os.getcwd(), "Cutler")
compiled_dir = os.path.join(base_dir, "Compiled")
os.makedirs(compiled_dir, exist_ok=True)
today_str = datetime.today().strftime("%Y%m%d")

# === Define Fund Scripts ===
fund_scripts = {
    "Allianz Global Investors": "Allianz.py",
    "ALPS Funds": "ALPS.py",
    "Amana (Saturna Capital)": "Amana.py",
    "American Century Investments (ACI)": "American_Century_Investments.py",
    "Appleseed Fund": "Appleseed.py",
    "Ariel Investments": "Ariel.py",
    "Artisan Partners": "Artisan.py",
    "Baird Asset Management": "Baird.py",
    "Baron Capital": "Baron.py",
    "Brookfield Asset Management": "Brookfield.py",
    "Buffalo Funds": "Buffalo.py",
    "Causeway Capital": "Causeway.py",
    "Cavanal Hill Funds": "CavanalHill.py",
    "Clarkston Capital": "Clarkston.py"
}

FUND_FOLDER_MAP = {
    "Amana (Saturna Capital)": "Amana",
    "American Century Investments (ACI)": "American_Century_Investments",
    "Allianz Global Investors": "Allianz",
    "ALPS Funds": "ALPS",
    "Appleseed Fund": "Appleseed",
    "Ariel Investments": "Ariel",
    "Artisan Partners": "Artisan",
    "Baird Asset Management": "Baird",
    "Baron Capital": "Baron",
    "Brookfield Asset Management": "Brookfield",
    "Buffalo Funds": "Buffalo",
    "Causeway Capital": "Causeway",
    "Cavanal Hill Funds": "CavanalHill",
    "Clarkston Capital": "Clarkston"
}

st.title("Cutler Capital: Full Mutual Fund Compilation")

if st.button("Download All Reports and Generate Compiled Excerpt"):
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    skipped_funds = []
    all_pdf_paths = []  # Correctly initialized

    total = len(fund_scripts)
    for i, (fund_name, script) in enumerate(fund_scripts.items()):
        status_placeholder.markdown(f"Running scraper for **{fund_name}**")
        fund_folder = FUND_FOLDER_MAP.get(fund_name)
        if not fund_folder:
            st.warning(f"Skipping unknown fund folder mapping: {fund_name}")
            continue
        fund_dir = os.path.join(base_dir, fund_folder, "downloads")
        os.makedirs(fund_dir, exist_ok=True)

        try:
            subprocess.run(["python", script], check=True, timeout=120)
        except subprocess.CalledProcessError as e:
            st.error(f"Script failed for {fund_name}: {e}")
            skipped_funds.append(fund_name)
            continue
        except subprocess.TimeoutExpired:
            st.warning(f"Script for {fund_name} timed out.")
            skipped_funds.append(fund_name)
            continue

        pdfs_found = False
        for file in os.listdir(fund_dir):
            if file.endswith("_Merged.pdf") and os.path.getsize(os.path.join(fund_dir, file)) > 0:
                file_path = os.path.join(fund_dir, file)
                all_pdf_paths.append((fund_name, file_path))
                pdfs_found = True

        if not pdfs_found:
            st.warning(f"No PDFs found for {fund_name} after running {script}")
            skipped_funds.append(fund_name)

        progress_bar.progress((i + 1) / total)

    if not all_pdf_paths:
        st.error("No valid PDFs found. Skipping merging and excerption.")
        sys.exit(1)

    compiled_merged_path = os.path.join(compiled_dir, f"Compiled_{today_str}_Merged.pdf")
    merger = PdfMerger()
    for _, path in all_pdf_paths:
        try:
            # Validate PDF before appending
            PdfReader(path)
            merger.append(path)
        except PdfReadError:
            st.warning(f"Skipping corrupted PDF: {os.path.basename(path)}")
            continue
    merger.write(compiled_merged_path)
    merger.close()
    st.success(f"Merged PDF saved to: {compiled_merged_path}")
    st.download_button("Download Merged PDF", compiled_merged_path, file_name=os.path.basename(compiled_merged_path))

    if skipped_funds:
        st.warning("The following funds were skipped:")
        for fund in skipped_funds:
            st.text(f"- {fund}")

    st.write("Starting excerption...")
    full_text = extract_full_text_from_pdf(compiled_merged_path)
    results_by_fund = {}

    for fund_name, _ in all_pdf_paths:
        if fund_name not in results_by_fund:
            results_by_fund[fund_name] = {}
        for ticker, company in tickers.items():
            paras = extract_company_paragraphs(full_text, company)
            filtered = filter_relevant_paragraphs(paras, tickers)
            if filtered:
                if company not in results_by_fund[fund_name]:
                    results_by_fund[fund_name][company] = []
                results_by_fund[fund_name][company].extend(filtered)

    for fund in results_by_fund:
        results_by_fund[fund] = remove_duplicate_paragraphs(results_by_fund[fund])

    output_pdf_path = os.path.join(compiled_dir, f"Excerpted_Compiled_{today_str}.pdf")
    c = canvas.Canvas(output_pdf_path, pagesize=LETTER)
    width, height = LETTER
    y = height - 50
    line_height = 14

    for fund, company_dict in results_by_fund.items():
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, f"{fund}")
        y -= line_height * 2

        for company, paragraphs in company_dict.items():
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, f"{company}")
            y -= line_height
            c.setFont("Helvetica", 12)
            for i, para in enumerate(paragraphs, 1):
                lines = textwrap.wrap(f"Paragraph {i}: {para}", width=100)
                for line in lines:
                    if y <= 50:
                        c.showPage()
                        y = height - 50
                        c.setFont("Helvetica", 12)
                    c.drawString(50, y, line)
                    y -= line_height
                y -= line_height
            y -= line_height * 2
            if y <= 50:
                c.showPage()
                y = height - 50

    c.save()
    st.success(f"Excerpted PDF saved to: {output_pdf_path}")
    st.download_button("Download Excerpted PDF", output_pdf_path, file_name=os.path.basename(output_pdf_path))
