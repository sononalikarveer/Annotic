import json
import os
from transcript_rules import is_silence, format_silence, apply_word_rules, format_time

def run():
    print("\\n[Step 4] Categorizing Data from Transcripts using External Rule Engine...")
    
    if not os.path.exists("raw_transcripts.json"):
        print("[!] raw_transcripts.json not found. Did you run Step 3?")
        return
        
    with open("raw_transcripts.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    final_segments = []
    last_word_end = 0.0
    
    for item in raw_data:
        start = item["start"]
        end = item["end"]
        word = item["word"]
        
        if not word:
            continue
            
        # Rule 11: Silence Block for gaps >= 2 seconds
        if is_silence(start, last_word_end):
            final_segments.append({
                "start": last_word_end,
                "end": start,
                "start_fmt": format_time(last_word_end),
                "end_fmt": format_time(start),
                "text": format_silence(),
                "Transcription": [format_silence()]
            })
            
        # Rules 1, 2, 4, 5, 9, 12, 13, 14, 15: Apply word-level taxonomic rules
        processed_word = apply_word_rules(word)
        
        # Enforce exactly one word per block (Rules 6 & 10)
        final_segments.append({
            "start": start,
            "end": end,
            "start_fmt": format_time(start),
            "end_fmt": format_time(end),
            "text": processed_word,
            "Transcription": [processed_word]
        })
        
        last_word_end = end
        
    output_data = {
        "id": 104980,
        "file_name": "target_audio.mp3",
        "annotations": [{"start": s["start_fmt"], "end": s["end_fmt"], "Transcription": s["Transcription"]} for s in final_segments]
    }
    
    # Save the specific final structure expected for creating segments
    with open("expected_output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    # Also save the utility segments array that Step 5 and 6 will rely heavily on for exact floating math
    with open("categorized_segments.json", "w", encoding="utf-8") as f:
        json.dump(final_segments, f, ensure_ascii=False, indent=4)
        
    print(f"[✓] Categorized {len(final_segments)} rules-compliant segments and saved to expected_output.json")

if __name__ == "__main__":
    run()
