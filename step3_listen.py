import json
from faster_whisper import WhisperModel

def run():
    print("\\n[Step 3] Listening to Audio with Faster-Whisper...")
    
    # Check if target_audio.mp3 exists
    try:
        open("target_audio.mp3", "r")
    except FileNotFoundError:
        print("[!] target_audio.mp3 not found. Did Step 1 run?")
        return

    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        "target_audio.mp3", 
        vad_filter=False, 
        word_timestamps=True,
        initial_prompt="This is an English recording. Please transcribe every single word exactly as it is spoken."
    )
    
    print(f"Detected language '{info.language}' with probability {info.language_probability}")
    
    raw_data = []
    # Save the absolute raw words as they come out of the engine
    for segment in segments:
        for word_info in segment.words:
            raw_data.append({
                "start": word_info.start,
                "end": word_info.end,
                "word": word_info.word.strip()
            })
            
    with open("raw_transcripts.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=4)
        
    print(f"[✓] Saved {len(raw_data)} raw words to raw_transcripts.json")

if __name__ == "__main__":
    run()
