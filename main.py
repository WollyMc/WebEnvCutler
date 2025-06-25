
import streamlit as st
import subprocess
import os
import threading
import time

# Define mutual fund scraper scripts
fund_scripts = {
    "Amana (Saturna Capital)": "03_14_25_Amana.py",
    "American Century Investments (ACI)": "03_14_25_ACI.py",
    "Allianz Global Investors": "03_14_25_Allianz.py",
    "Alger Funds": "03_14_25_Alger.py",
    "ALPS Funds": "03_14_25_ALPS.py",
    "Appleseed Fund": "03_14_25_Appleseed.py",
    "Ariel Investments": "03_14_25_Ariel.py",
    "Artisan Partners": "03_14_25_Artisan.py",
    "Baird Asset Management": "03_14_25_Baird.py",
    "Baron Capital": "03_14_25_Baron.py",
    "Brookfield Asset Management": "03_14_25_Brookfield.py",
    "Buffalo Funds": "03_14_25_Buffalo.py",
    "Causeway Capital": "03_14_25_Causeway.py",
    "Cavanal Hill Funds": "03_14_25_CavanalHill.py",
    "Clipper Fund": "03_14_25_Clipper.py",
    "Dodge & Cox":"03_14_25_DodgeCox.py",
    "Fidelity Investments": "03_14_25_Fidelity.py",
    "First Eagle Fund": "03_14_25_FirstEagleFund.py",
    "Gabelli Funds": "03_14_25_Gabelli.py",
    "Harbor Funds": "03_14_25_Harbor.py",
    "Longleaf Partners": "03_14_25_Longleaf.py",
    "MFS Investment Management": "03_14_25_MFS.py",
    "Oakmark Fund": "03_14_25_Oakmark.py",
    "Poplar Forest Funds": "03_14_25_PFF.py",
    "Sequoia Funds": "03_14_25_Sequoia.py",
    "Touchstone Mutual Funds": "03_14_25_Touchstone.py",
    "Tweedy Browne Funds": "03_14_25_Tweedy.py",
    "T. Rowe Price": "03_14_25_TRowe.py",
    "Transamerica": "03_14_25_Transamerica.py",
    "Value Line Funds": "03_14_25_ValueLine.py",
    "Victory Funds": "03_14_25_Victory.py",
    "Virtus Funds": "03_14_25_Virtus.py",
    "Wasatch Global Funds": "03_14_25_Wasatch.py",
    "Weitz Investments": "03_14_25_Weitz.py",
    "William Blair Funds": "03_14_25_William.py"
}

FUND_FOLDER_MAP = {
    "Amana (Saturna Capital)": "Amana",
    "American Century Investments (ACI)": "American_Century_Investments",
    "Allianz Global Investors":"Allianz",
    "Alger Funds": "Alger",
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
    "Clipper Fund": "Clipper",
    "Dodge & Cox": "Dodge&Cox",
    "Fidelity Investments": "Fidelity",
    "First Eagle Fund": "FirstEagleFund",
    "Gabelli Funds": "Gabelli",
    "Harbor Funds": "Harbor",
    "Longleaf Partners": "Longleaf",
    "MFS Investment Management": "MFS",
    "Oakmark Fund": "Oakmark",
    "Poplar Forest Funds": "Poplar_Forest_Funds",
    "Sequoia Funds": "Sequoia",
    "Touchstone Mutual Funds": "Touchstone",
    "Tweedy Browne Funds": "Tweedy",
    "T. Rowe Price": "T_Rowe_Price",
    "Transamerica": "Transamerica",
    "Value Line Funds": "ValueLine",
    "Victory Funds": "Victory",
    "Virtus Funds": "Virtus",
    "Wasatch Global Funds": "Wasatch",
    "Weitz Investments": "Weitz",
    "William Blair Funds": "WilliamBlair"
}

EXCERPT_SCRIPT = os.path.join(os.getcwd(), "excerpt.py")
PODCAST_SCRIPT = os.path.join(os.getcwd(), "podcast_processor.py")

# UI start
st.title("Cutler Capital Management")

workflow = st.radio("Select Workflow", ["Mutual Fund Reports", "Podcast Processing"], horizontal=True)

# === MUTUAL FUND WORKFLOW ===
if workflow == "Mutual Fund Reports":
    st.write("Select one or multiple mutual fund families to scrape their latest reports.")

    select_all = st.checkbox("Select All")
    if select_all:
        selected_funds = list(fund_scripts.keys())
    else:
        selected_funds = st.multiselect("Choose Mutual Fund Families", list(fund_scripts.keys()))

    def run_scraper(script_path, result_holder):
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        result_holder.append(result) 

    if st.button("Download Reports"):
        if not selected_funds:
            st.warning("Please select at least one mutual fund to scrape.")
        else:
            st.write("Starting the scraping process...")
            base_dir = "Cutler"
            os.makedirs(base_dir, exist_ok=True)
            completed_funds = []

            total = len(selected_funds)
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            status_placeholder = st.empty()

            for i, fund in enumerate(selected_funds):
                folder_name = FUND_FOLDER_MAP.get(fund, fund.replace(" ", "_"))
                fund_folder = os.path.join(base_dir, folder_name)
                os.makedirs(fund_folder, exist_ok=True)

                script_path = fund_scripts[fund]
                status_placeholder.markdown(f"Scraping: **{fund}**")

                result_holder = []
                thread = threading.Thread(target=run_scraper, args=(script_path, result_holder))
                thread.start()

                fake_progress = 0.0
                step = 0.01
                while thread.is_alive():
                    time.sleep(0.1)
                    fake_progress = min(fake_progress + step, 0.95)
                    overall_progress = (i + fake_progress) / total
                    progress_bar.progress(overall_progress)

                thread.join()
                progress_bar.progress((i + 1) / total)

                result = result_holder[0]
                if result.returncode == 0:
                    st.success(f"{fund} reports downloaded successfully!")
                    completed_funds.append(fund)
                else:
                    st.error(f"Error in scraping {fund}.")
                    st.text(result.stderr)

            status_placeholder.markdown("Scraping completed.")
            if completed_funds:
                st.session_state["scraping_done"] = True
                st.session_state["completed_funds"] = completed_funds

    def run_excerpt(fund_args, result_holder):
        result = subprocess.run(["python", EXCERPT_SCRIPT, fund_args], capture_output=True, text=True)
        result_holder.append(result)

    if st.session_state.get("scraping_done", False):
        st.write("---")
        st.subheader("Generate Excerpt Reports")

        if st.button("Generate Excerpts"):
            st.write("🔍 Starting the excerpt generation process...")

            completed_funds = st.session_state["completed_funds"]
            total = len(completed_funds)

            progress_bar = st.progress(0)
            status_placeholder = st.empty()

            for i, fund in enumerate(completed_funds):
                folder_name = FUND_FOLDER_MAP.get(fund, fund.replace(" ", "_"))
                status_placeholder.markdown(f"Generating excerpt for **{fund}**...")

                result_holder = []
                thread = threading.Thread(target=run_excerpt, args=(folder_name, result_holder))
                thread.start()

                fake_progress = 0.0
                step = 0.01
                while thread.is_alive():
                    time.sleep(0.1)
                    fake_progress = min(fake_progress + step, 0.95)
                    overall_progress = (i + fake_progress) / total
                    progress_bar.progress(overall_progress)

                thread.join()
                result = result_holder[0]
                progress_bar.progress((i + 1) / total)

                if result.returncode == 0:
                    st.success(f"Excerpt for {fund} generated successfully!")
                else:
                    st.error(f"❌ Error generating excerpt for {fund}.")
                    st.text(result.stderr)

            status_placeholder.markdown("✅ All excerpts generated successfully!")

# === PODCAST WORKFLOW ===
elif workflow == "Podcast Processing":
    st.subheader("🎧 Process a Podcast (Manual Entry)")

    podcast_name_input = st.text_input("Enter a short name for the podcast (no spaces):")
    podcast_url_input = st.text_input("Enter a valid podcast URL (yt-dlp supported):")

    if st.button("Process Podcast"):
        if not podcast_name_input or not podcast_url_input:
            st.warning("Please enter both the podcast name and a valid URL.")
        else:
            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            def run_manual_podcast(name, url, result_holder):
                result = subprocess.run(["python", PODCAST_SCRIPT, name, url], capture_output=True, text=True)
                result_holder.append(result)

            result_holder = []
            thread = threading.Thread(target=run_manual_podcast, args=(podcast_name_input, podcast_url_input, result_holder))
            thread.start()

            fake_progress = 0.0
            step = 0.01
            while thread.is_alive():
                time.sleep(0.1)
                fake_progress = min(fake_progress + step, 0.95)
                progress_bar.progress(fake_progress)

            thread.join()
            progress_bar.progress(1.0)

            result = result_holder[0]
            if result.returncode == 0:
                st.success("✅ Podcast processed successfully!")
            else:
                st.error("❌ Podcast processing failed.")
                st.text(result.stderr)
