import whisper
import sys
from pathlib import Path

audio_file = Path("backend/data/podcasts/nerdcast_1018_-_fallout_2_o_que_acontece_em_new_vegas.mp3")

print(f"Audio file exists: {audio_file.exists()}")
print(f"Audio file path: {audio_file.absolute()}")

print("\nLoading Whisper tiny model...")
model = whisper.load_model("tiny", device="cpu")

print("Transcribing first 30 seconds...")
try:
    result = model.transcribe(str(audio_file.absolute()), language="pt", duration=30)
    print(f"\nSuccess! Transcript: {result['text'][:200]}...")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
