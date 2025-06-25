# excerpt.py
import os
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from excerption_base import main as refine_excerpt, save_results_to_pdf

# === Directory Setup ===
BASE_DIR = os.path.join(os.getcwd(), "Cutler", "Compiled")
today_str = datetime.today().strftime("%Y%m%d")

merged_input_path = r"C:\Users\AI Admin\Documents\WebEnvTest\03-28-25\Full\Cutler\Compiled\Compiled_20250606_Merged.pdf"
if not os.path.exists(merged_input_path):
    print(f" Merged PDF not found at: {merged_input_path}")
    exit()

print(f" Found merged PDF: {merged_input_path}")

# === Split into Batches of 20 Pages ===
try:
    reader = PdfReader(merged_input_path)
    total_pages = len(reader.pages)
    print(f" Total pages in merged PDF: {total_pages}")

    batch_size = 20
    batch_count = (total_pages + batch_size - 1) // batch_size  # ceil division

    for batch_num in range(batch_count):
        start = batch_num * batch_size
        end = min(start + batch_size, total_pages)

        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        batch_path = os.path.join(BASE_DIR, f"Batch_{batch_num+1}_{start+1}_to_{end}.pdf")
        with open(batch_path, "wb") as f_out:
            writer.write(f_out)

        print(f" Created batch: {batch_path}")

        # === Run Excerption on This Batch ===
        print(f" Running excerption on Batch {batch_num+1} ({start+1} to {end})...")
        try:
            results = refine_excerpt(batch_path)
            if results:
                excerpt_output_path = os.path.join(BASE_DIR, f"Excerpted_Batch_{batch_num+1}_{start+1}_to_{end}.pdf")
                save_results_to_pdf(results, excerpt_output_path)
                print(f" Excerpted saved: {excerpt_output_path}")
            else:
                print(f"ℹ No relevant content found in Batch {batch_num+1}")
        except Exception as e:
            print(f" Error processing Batch {batch_num+1}: {e}")

except Exception as e:
    print(f" Failed to process the merged PDF: {e}")
