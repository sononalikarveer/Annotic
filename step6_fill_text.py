import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    print("\\n[Step 6] Filling React Textareas with Categorized Transcriptions...")
    
    try:
        with open("categorized_segments.json", "r", encoding="utf-8") as f:
            segments = json.load(f)
    except FileNotFoundError:
        print("[!] categorized_segments.json not found. Did you run Step 4?")
        return
        
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "annotic.in" in page.url:
                    target_page = page
                    break
            if target_page: break
            
        print(f"Targeting: {target_page.url}")
        
        # Original text-fill functionality restored directly from Git log history Request
        textareas = await target_page.locator('textarea.auto-resizable-textarea').all()
        print(f"Discovered {len(textareas)} physical text boxes on screen for {len(segments)} segments.")
        
        filled = 0
        for index, seg in enumerate(segments):
            text = seg["text"]
            try:
                if textareas:
                    # Accommodate the occasional 'sub_0' generic project block at index 0
                    target_index = min(index + 1, len(textareas) - 1)
                    target_input = textareas[target_index]
                    
                    # Scroll into view so the Virtual DOM doesn't collapse it before the text arrives
                    await target_input.scroll_into_view_if_needed()
                    await asyncio.sleep(0.1)
                    
                    # Instead of flat .fill, emulate keyboard typing
                    await target_input.click(timeout=1000)
                    await target_page.keyboard.press("Control+A")
                    await target_page.keyboard.press("Backspace")
                    await target_page.keyboard.type(text, delay=10)
                    await target_page.keyboard.press("Escape")
                    
                    print(f"  [+] Filled Segment {index+1}: {text}")
                    filled += 1
                else:
                    print(f"  [!] Missing physical textbox layout for segment {index+1}.")
            except Exception as e:
                print(f"  [!] Failed applying text '{text}' on segment {index+1}: {e}")

        print(f"[✓] Automation complete! {filled}/{len(segments)} blocks filled and blurred.")

if __name__ == "__main__":
    asyncio.run(run())
