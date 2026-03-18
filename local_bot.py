import asyncio
import os
import json
import requests
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from faster_whisper import WhisperModel

# The target URL where we expect to find the audio and canvas
TARGET_URL = "https://annotic.in/#/projects/85/AudioTranscriptionLandingPage/60786"

async def extract_audio_url(page):
    print("Looking for audio element on the page...")
    # Wait for the audio element to be present in the DOM
    try:
        audio_element = await page.wait_for_selector('audio', timeout=10000)
        src = await audio_element.get_attribute('src')
        
        if src:
            # Handle relative URLs
            if src.startswith('/'):
                src = urljoin(page.url, src)
            print(f"[{chr(10004)}] Found audio source: {src}")
            return src
        else:
            print("Audio element found, but it has no 'src' attribute.")
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
    # Returns 0:00:00.000000 format as requested in the JSON image
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    microsecs = int(round((seconds % 1) * 1e6))
    return f"{hours}:{minutes:02d}:{secs:02d}.{microsecs:06d}"

def process_audio(filename):
    print("\\nInitializing Faster-Whisper model... (this may take a minute on first run)")
    # 'base' model is faster but less accurate. You can try 'small' or 'medium' for better transcriptions.
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    print("Pre-processing and transcribing audio with word-level timestamps...")
    # We disable vad_filter to manually detect silences > 2s and use word_timestamps for 25ms gap detection
    segments, info = model.transcribe(
        filename, 
        vad_filter=False, 
        word_timestamps=True,
        # Rule 1, 4, 5, 9: Initial prompt to encourage verbatim transcription with repetitions and fillers
        initial_prompt="This is an English audio recording. Please transcribe every single word, including all repetitions, stammering, and filler sounds like 'uh', 'um', 'ah' exactly as they are spoken. Do not clean up or correct the speech."
    )

    print(f"Detected language '{info.language}' with probability {info.language_probability}")

    final_segments = []
    last_word_end = 0.0

    print("Applying transcription rules (one word per block, verbatim text, <SIL> tags)...")
    
    for segment in segments:
        for word_info in segment.words:
            word_text = word_info.word.strip()
            if not word_text:
                continue
                
            start = word_info.start
            end = word_info.end
            
            # Rule 11: Silence (<SIL>) -> Use when pause > 2 seconds
            if start - last_word_end > 2.0 and last_word_end > 0:
                final_segments.append({
                    "start": last_word_end,
                    "end": start,
                    "start_fmt": format_time(last_word_end),
                    "end_fmt": format_time(start),
                    "text": "<SIL></SIL>",
                    "Transcription": ["<SIL></SIL>"]
                })
            
            # Rule 12: Fillers -> 'ah', 'uh', 'um'
            if word_text.lower() in ["ah", "uh", "um", "hmm", "er"]:
                word_text = f"<FIL>{word_text}</FIL>"
                
            # ONE block = ONE word/sound as requested
            final_segments.append({
                "start": start,
                "end": end,
                "start_fmt": format_time(start),
                "end_fmt": format_time(end),
                "text": word_text,
                "Transcription": [word_text]
            })
            
            last_word_end = end

    print(f"\\n[{chr(10004)}] Processing complete! {len(final_segments)} rules-compliant segments generated:")
    for i, seg in enumerate(final_segments[:10]): # print first 10 for log brevity
        print(f"  Segment {i+1}: [{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text']}")
    if len(final_segments) > 10:
        print(f"  ... and {len(final_segments)-10} more segments.")
        
    # Generate the JSON file exactly matching the output format image
    output_data = {
        "id": 13945, # Placeholder ID matching the screenshot structure
        "file_name": os.path.basename(filename),
        "annotations": []
    }
    
    for seg in final_segments:
        output_data["annotations"].append({
            "start": seg["start_fmt"],
            "end": seg["end_fmt"],
            "Transcription": seg["Transcription"]
        })
        
    json_filename = "expected_output.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print(f"[{chr(10004)}] Saved JSON formatted output to {json_filename}")
        
    return final_segments

async def main():
    async with async_playwright() as p:
        try:
            print("Connecting to existing Chrome session on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print(f"[{chr(10004)}] Connected!")
            
            # Find the target annotic page among open tabs
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    if "annotic.in" in page.url:
                        target_page = page
                        break
                if target_page:
                    break
            
            if not target_page:
                print(f"Could not find a tab open to {TARGET_URL}.")
                print("Opening a new tab to the target URL...")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                target_page = await context.new_page()
                await target_page.goto(TARGET_URL)
            else:
                print(f"[{chr(10004)}] Found target page tab: {target_page.url}")
                await target_page.bring_to_front()
            
            # Phase 1: Download Audio
            audio_url = await extract_audio_url(target_page)
            if not audio_url:
                print("Aborting: Could not extract audio to process.")
                await browser.close()
                return
                
            audio_filename = download_audio(audio_url)
            if not audio_filename:
                print("Aborting: Could not download audio.")
                await browser.close()
                return
            # Phase 2: Process Audio locally with Whisper
            segments = process_audio(audio_filename)
            
            # Phase 3: Create All Segments on the Canvas First
            print("\\n[Phase 3: Plotting all Segments on Canvas via Click-and-Drag]")
            print("To ensure clean partitions, make sure the Canvas is completely empty/reset before starting this!")
            
            # 1. Dynamically calculate the Canvas Mathematical Ratio
            try:
                # Find Canvas Width
                rect = await target_page.locator('canvas').first.bounding_box()
                if not rect:
                    print("  [!] Could not find <canvas> element. Cannot perform drag-and-drop.")
                    await browser.close()
                    return
                    
                canvas_width = rect['width']
                canvas_x = rect['x']
                canvas_y = rect['y']
                
                # Target the exact middle height of the canvas
                y_coord = canvas_y + (rect['height'] / 2.0)
                
                # Find Total Audio Duration
                total_duration = await target_page.evaluate("document.getElementById('audio-panel').duration")
                if not total_duration:
                    print("  [!] Could not read audio duration from #audio-panel.")
                    await browser.close()
                    return
                    
                pixels_per_second = canvas_width / total_duration
                print(f"  -> Calculated Ratio: {pixels_per_second:.2f} pixels per second (Width: {canvas_width}px, Audio: {total_duration}s)")
            except Exception as e:
                print(f"  [!] Failed to calculate Canvas Math. Error: {e}")
                await browser.close()
                return

            # 2. Draw all physical segments first
            for index, segment in enumerate(segments):
                start_time = segment["start"]
                end_time = segment["end"]
                
                # Math: Start_X = (Start_Timestamp * Ratio) + Canvas_X_Offset
                start_x = (start_time * pixels_per_second) + canvas_x
                end_x = (end_time * pixels_per_second) + canvas_x
                
                print(f"-> Dragging Segment {index+1}: Time [{start_time:.2f}s - {end_time:.2f}s] -> Pixels [{start_x:.1f}px - {end_x:.1f}px]")
                
                try:
                    # Move exactly to the start position
                    await target_page.mouse.move(start_x, y_coord)
                    
                    # Hold Shift, as many annotators require this to draw new regions instead of scrolling
                    await target_page.keyboard.down("Shift")
                    
                    # Mouse down (Start Segmenting)
                    await target_page.mouse.down()
                    await asyncio.sleep(0.05)
                    # Drag smoothly to the end position
                    await target_page.mouse.move(end_x, y_coord, steps=25)
                    await asyncio.sleep(0.05)
                    # Release (Create segment)
                    await target_page.mouse.up()
                    
                    await target_page.keyboard.up("Shift")
                    
                    await asyncio.sleep(0.1) # Small pause to let the website's JS register the event
                except Exception as e:
                    print(f"   [!] Failed to draw segment {index+1}. Error: {e}")
                
            print("\\nFinished drawing partitions! Waiting for UI blocks to fully render...")
            await asyncio.sleep(2.0)
                
            # Phase 4: Fill the generated text blocks
            print("\\n[Phase 4: Filling text into generated Canvas Blocks]")
            textareas = await target_page.locator('textarea.auto-resizable-textarea').all()
            print(f"Found {len(textareas)} text boxes on the canvas for {len(segments)} segments.")
            
            for index, segment in enumerate(segments):
                text = segment["text"]
                try:
                    if textareas:
                        # Assuming the new block gets placed in order
                        target_index = min(index + 1, len(textareas) - 1)  # +1 because 1 block existed initially usually
                        target_input = textareas[target_index]
                        
                        await target_input.fill(text)
                        print(f"   [+] Filled segment {index+1}: {text}")
                    else:
                        print(f"   [!] Could not find text boxes to fill for segment {index+1}.")
                except Exception as e:
                    print(f"   [!] Failed to enter text for segment {index+1}. Error: {e}")
            
            print("\\n[✔] Automation complete! Please review the Canvas.")
            
            await browser.close()
            
        except Exception as e:
            import traceback
            print(f"\\nError during execution:")
            traceback.print_exc()
            print("Please ensure you have started Chrome with: chrome.exe --remote-debugging-port=9222 --user-data-dir='C:\\sel_profile'")

if __name__ == "__main__":
    asyncio.run(main())
