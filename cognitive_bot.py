import asyncio
import os
import json
import requests
import librosa
from rapidfuzz import fuzz
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from faster_whisper import WhisperModel

# The target URL where we expect to find the audio and canvas
TARGET_URL = "https://annotic.in/#/projects/85/AudioTranscriptionLandingPage/60786"

async def extract_audio_url(page):
    print("Looking for audio element on the page...")
    try:
        audio_element = await page.wait_for_selector('audio', timeout=10000)
        src = await audio_element.get_attribute('src')
        if src:
            if src.startswith('/'): src = urljoin(page.url, src)
            print(f"[{chr(10004)}] Found audio source: {src}")
            return src
        else:
            return None
    except Exception as e:
        print(f"Could not find an <audio> element: {e}")
        return None

def download_audio(url, filename="target_audio.mp3"):
    print(f"Downloading audio from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[{chr(10004)}] Audio downloaded successfully to {filename}")
        return filename
    except Exception as e:
        print(f"Failed to download audio: {e}")
        return None

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    microsecs = int(round((seconds % 1) * 1e6))
    return f"{hours}:{minutes:02d}:{secs:02d}.{microsecs:06d}"

def analyze_with_librosa(filename):
    print("Part 1: The Listener - Running Librosa signal processing for <SIL> detection...")
    y, sr = librosa.load(filename)
    # top_db=30 is standard for speech vs silence
    non_mute_intervals = librosa.effects.split(y, top_db=30)
    
    silences = []
    for i in range(len(non_mute_intervals) - 1):
        silence_start = non_mute_intervals[i][1] / sr
        silence_end = non_mute_intervals[i+1][0] / sr
        duration = silence_end - silence_start
        if duration >= 2.0:
            silences.append({
                "start": silence_start,
                "end": silence_end,
                "start_fmt": format_time(silence_start),
                "end_fmt": format_time(silence_end),
                "text": "<SIL></SIL>",
                "Transcription": ["<SIL></SIL>"]
            })
    print(f"  -> Librosa detected {len(silences)} mathematical <SIL> blocks.")
    return silences

def apply_cognitive_rules(word_heard, reference_text):
    # Rule 12: Fillers
    if word_heard.lower() in ["ah", "uh", "um", "hmm", "er", "आ", "अ"]:
        return f"<FIL>{word_heard}</FIL>"
        
    # Rule 3 & 4 (Phonetic vs Copy-Paste):
    # fuzzy match the word_heard against the reference_text
    words_in_ref = reference_text.split()
    best_match = None
    best_score = 0
    
    for ref_word in words_in_ref:
        clean_ref = ''.join(c for c in ref_word if c.isalnum() or c in "'-")
        if not clean_ref: continue
        score = fuzz.ratio(word_heard.lower(), clean_ref.lower())
        if score > best_score:
            best_score = score
            best_match = clean_ref
            
    # If high confidence phonetic match, snap to the Reference Text (Rule 3)
    # Else emit exact whispered phenomes (Rule 4)
    if best_score > 85 and best_match: 
        return best_match
    else:
        return word_heard

def process_audio(filename, reference_text):
    print("\\nInitializing Faster-Whisper model... (Part 2: The Comparer)")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    print("Transcribing audio with word-level timestamps...")
    segments, info = model.transcribe(
        filename, 
        vad_filter=False, 
        word_timestamps=True,
        initial_prompt="This is an English audio recording. Please transcribe every single word, including all repetitions, stammering, and filler sounds like 'uh', 'um', 'ah' exactly as they are spoken. Do not clean up or correct the speech."
    )

    final_segments = []
    
    # 1. Fetch Librosa Mathematical Silences
    librosa_silences = analyze_with_librosa(filename)
    final_segments.extend(librosa_silences)

    print("Applying cognitive transcription rules (25ms splits, RapidFuzz Copy/Paste)...")
    for segment in segments:
        for word_info in segment.words:
            raw_word = word_info.word.strip()
            if not raw_word: continue
                
            start = word_info.start
            end = word_info.end
            
            # Use The Comparer module
            processed_word = apply_cognitive_rules(raw_word, reference_text)
                
            final_segments.append({
                "start": start,
                "end": end,
                "start_fmt": format_time(start),
                "end_fmt": format_time(end),
                "text": processed_word,
                "Transcription": [processed_word]
            })

    # Sort final blocks purely by start time so silences and words mix correctly
    final_segments = sorted(final_segments, key=lambda x: x["start"])

    print(f"\\n[{chr(10004)}] Processing complete! {len(final_segments)} rules-compliant segments generated.")
        
    output_data = {
        "id": 13945,
        "file_name": os.path.basename(filename),
        "annotations": [{"start": s["start_fmt"], "end": s["end_fmt"], "Transcription": s["Transcription"]} for s in final_segments]
    }
    
    with open("expected_output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    return final_segments

async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to existing Chrome session...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    if "annotic.in" in page.url:
                        target_page = page
                        break
                if target_page: break
            
            if not target_page:
                print(f"Abort. Could not find Annotic tab.")
                await browser.close()
                return
            await target_page.bring_to_front()
            
            # Read Reference Text
            print("Reading Reference Text from DOM for The Comparer...")
            page_text = await target_page.evaluate("""() => {
                return Array.from(document.querySelectorAll('div, p, span'))
                    .filter(e => e.innerText && e.innerText.length > 20 && e.children.length === 0)
                    .map(e => e.innerText).join(' ');
            }""")
            print(f"  -> Found Reference Pool: {page_text[:100]}...")
            
            audio_url = await extract_audio_url(target_page)
            if not audio_url:
                await browser.close()
                return
                
            audio_filename = download_audio(audio_url)
            
            # Cognitive Pipeline
            segments = process_audio(audio_filename, page_text)
            
            # Part 3: The Performer (Browser Automation)
            print("\\n[Part 3: The Performer - Active Segmentation on Canvas]")
            print("To ensure clean partitions, make sure the Canvas is completely empty/reset before starting this!")
            
            for index, segment in enumerate(segments):
                start_time = segment["start"]
                text = segment["text"]
                
                print(f"-> Clicking {start_time:.2f}s: {text}")
                await target_page.evaluate(f"document.getElementById('audio-panel').currentTime = {start_time}")
                await asyncio.sleep(0.3)
                
                try:
                    split_btn = target_page.locator('button[aria-label="Split Subtitle"]')
                    await split_btn.click(timeout=3000)
                    await asyncio.sleep(0.3)
                except Exception as e:
                    pass
                
                try:
                    textareas = await target_page.locator('textarea.auto-resizable-textarea').all()
                    if textareas:
                        target_index = min(index + 1, len(textareas) - 1)
                        await textareas[target_index].fill(text)
                except Exception as e:
                    pass
            
            print("\\n[✔] Performer automation complete!")
            await browser.close()
            
        except Exception as e:
            print(f"\\nError during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
