# Annotic Automation Pipeline

This project contains a 6-step Python automation pipeline designed to process transcriptions and segments for the Annotic platform using Playwright and Faster-Whisper.

## Prerequisites
- Python 3.9+
- Microsoft Edge or Google Chrome running with remote-debugging enabled:
  `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\sel_profile"`
- Faster-Whisper, Playwright, and dependencies installed via pip.

## Pipeline Steps

### 1. `step1_scrape.py`
Scrapes the original raw reference text from the Annotic page and splits it into an array for processing.

### 2. `step2_delete.py`
Clears out all existing blocks and segments on Annotic. It iterates backwards over the DOM components to physically click the "Trash" icon, ensuring a fresh blank canvas for the new segments.

### 3. `step3_listen.py`
Uses `faster-whisper` (offline transcription) to listen to the audio stream in full. It uses advanced prompts to capture raw verbatim speech (including repetitions, stammers, and Hindi/English dialects) without sanitizing the output.

### 4. `step4_categorize.py`
Passes the raw audio transcription and the reference text into the rules engine (`transcript_rules.py`). It applies a strict 20-point taxonomy rule system (incorporating `<SIL>`, `<FIL>`, `<MB>`, `<NOISE>`, `<ADULT>`, etc.) and slices the transcription into timed segments.

### 5. `step5_create_segments.py`
Creates the physical segment blocks on Annotic's audio wave canvas using Shift+Drag simulation. It dynamically adjusts the Timeline Scale via native mouse clicks to enforce zoom constraints, then ensures segments are separated by a minimum 4px gap to prevent merging.

### 6. `step6_fill_text.py`
Injects the categorized verbatim Hindi/English strings into the newly spawned React textareas. It bypasses React Synthetic event issues by sequentially scrolling into view, clicking the native DOM nodes, clearing the inputs, and typing the strings naturally.

## Rule Engine (`transcript_rules.py`)
This module houses the custom transcription logic required to match the audio verbatim against the expected text. It handles pauses, stammers, speaker tags, and prevents AI models from stripping out critical filler words.

## Usage
Ensure the browser is running on port 9222, navigate to the targeted Annotic task, and run the scripts sequentially from 1 to 6.
