# excerpt.py
import os
import sys
from PyPDF2 import PdfMerger
from excerption_base import main as refine_excerpt, save_results_to_pdf

BASE_DIR = os.path.join(os.getcwd(), "Cutler")

FUND_FOLDER_MAP = {
    "American Century Investments (ACI)": "American_Century_Investments",
    "Baron Capital": "Baron",
    "Fidelity Investments": "Fidelity",
    "MFS Investment Management": "MFS",
    "Poplar Forest Funds": "Poplar_Forest_Funds",
    "T. Rowe Price": "T_Rowe_Price"
}

def merge_pdfs(pdf_paths, merged_output_path):
    merger = PdfMerger()
    for pdf in pdf_paths:
        merger.append(pdf)
    merger.write(merged_output_path)
    merger.close()
    return merged_output_path

def process_fund(fund_name):
    folder_name = FUND_FOLDER_MAP.get(fund_name, fund_name.replace(" ", "_"))
    fund_folder = os.path.join(BASE_DIR, folder_name)
    downloads_dir = os.path.join(fund_folder, "downloads")
    excerpted_dir = os.path.join(fund_folder, "excerpted")
    os.makedirs(excerpted_dir, exist_ok=True)

    print(f"\n--- Processing: {fund_name} ---")

    # Check for pre-merged file first
    merged_pdf_path = None
    for f in os.listdir(downloads_dir):
        if f.endswith("_Merged.pdf"):
            merged_pdf_path = os.path.join(downloads_dir, f)
            print(f" Found pre-merged PDF: {f}")
            break

    # If no pre-merged file, try to find single or multiple PDFs to work with
    if not merged_pdf_path:
        pdf_paths = [
            os.path.join(downloads_dir, f)
            for f in os.listdir(downloads_dir)
            if f.endswith(".pdf")
        ]

        if not pdf_paths:
            print(f" No PDFs found in {downloads_dir}. Skipping.")
            return

        if len(pdf_paths) == 1:
            merged_pdf_path = pdf_paths[0]
            print(f"Using single PDF: {os.path.basename(merged_pdf_path)}")
        else:
            merged_name = f"{folder_name}_Merged.pdf"
            merged_pdf_path = os.path.join(excerpted_dir, merged_name)
            merge_pdfs(pdf_paths, merged_pdf_path)
            print(f"Merged {len(pdf_paths)} PDFs → {merged_pdf_path}")

    # Run excerption
    try:
        print(" Running paragraph-level filtering...")
        results = refine_excerpt(merged_pdf_path)
        if results:
            out_name = f"Excerpted_{folder_name}.pdf"
            output_path = os.path.join(excerpted_dir, out_name)
            save_results_to_pdf(results, output_path)
            print(f" Excerpt saved to: {output_path}")
        else:
            print(f" No relevant content found in: {merged_pdf_path}")
    except Exception as e:
        print(f" Error processing {merged_pdf_path}: {e}")

if __name__ == "__main__":
    selected_funds = sys.argv[1:]

    if not selected_funds:
        print(" No mutual fund names passed. Exiting.")
        sys.exit(1)

    for fund in selected_funds:
        process_fund(fund)

    print("\n Excerpt generation completed.")


