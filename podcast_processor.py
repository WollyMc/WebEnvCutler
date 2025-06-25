
import os
import subprocess
import requests
import yt_dlp
from pathlib import Path
from excerption_base import main as refine_excerpt, save_results_to_pdf
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Base directory for storing podcasts and transcripts
BASE_DIR = Path("Cutler/Podcasts")
BASE_DIR.mkdir(parents=True, exist_ok=True)

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def download_audio(page_url, podcast_name):
    podcast_dir = BASE_DIR / podcast_name
    podcast_dir.mkdir(parents=True, exist_ok=True)

    output_path = podcast_dir / f"{podcast_name}.%(ext)s"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path),
        'ffmpeg_location': r"C:\ffmpeg\bin",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    print(f"Downloading audio for {podcast_name}...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([page_url])
    except yt_dlp.utils.DownloadError as e:
        print(f"[ERROR] yt-dlp failed: {e}")
        return None

    return podcast_dir / f"{podcast_name}.mp3"

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

def refine_excerpt_from_transcript(paragraphs):
    from tickers import tickers
    from excerption_base import filter_relevant_paragraphs, remove_duplicate_paragraphs
    results = {"Transcript": filter_relevant_paragraphs(paragraphs, tickers)}
    return remove_duplicate_paragraphs(results)

def process_podcast(podcast_name, audio_url):
    print(f"\nProcessing Podcast: {podcast_name}")
    audio_path = download_audio(audio_url, podcast_name)
    if not audio_path or not audio_path.exists():
        print(f"Audio download failed for {podcast_name}")
        return

    print("Transcribing audio...")
    transcript = transcribe_audio(audio_path)

    podcast_dir = BASE_DIR / podcast_name
    transcript_path = podcast_dir / f"{podcast_name}_transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as file:
        file.write(transcript)

    print("Applying excerption logic...")
    paragraphs = transcript.split("\n\n")
    results = refine_excerpt_from_transcript(paragraphs)

    excerpted_dir = podcast_dir / "excerpted"
    excerpted_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = excerpted_dir / f"Excerpted_{podcast_name}.pdf"
    save_results_to_pdf(results, str(output_pdf))
    print(f"Excerpt saved at: {output_pdf}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python podcast_processor.py <PodcastName> <ValidPodcastURL>")
        sys.exit(1)

    podcast_name = sys.argv[1]
    podcast_url = sys.argv[2]

    process_podcast(podcast_name, podcast_url)
