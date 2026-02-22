import whisper
import sys
from pathlib import Path

from backend.app.core.logger import logger, format_path

audio_file = Path("backend/data/podcasts/nerdcast_1018_-_fallout_2_o_que_acontece_em_new_vegas.mp3")

logger.info(f"Audio file exists: {audio_file.exists()}")
logger.info(f"Audio file: {format_path(audio_file)}")

logger.info("\nLoading Whisper tiny model...")
model = whisper.load_model("tiny", device="cpu")

logger.info("Transcribing first 30 seconds...")
try:
    result = model.transcribe(str(audio_file), language="pt", duration=30)
    logger.success(f"\nSuccess! Transcript: {result['text'][:200]}...")
except Exception as e:
    logger.error(f"\nError: {e}")
    import traceback
    traceback.print_exc()
