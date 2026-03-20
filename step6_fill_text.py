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
        
        filled = 0
        for index, seg in enumerate(segments):
            text = seg["text"]
            try:
                # Re-query all currently rendered blocks to survive Virtual DOM shifting
                blocks = await target_page.locator('div[id^="sub_"]').all()
                if not blocks:
                    print("  [!] No blocks found on screen.")
                    break
                    
                # We need the physical container to sort by Y. Or just trust DOM order.
                # Assuming DOM order matches chronological order (it almost always does for React appending)
                target_block_index = min(index + 1 if len(blocks) > index else len(blocks) - 1, len(blocks) - 1)
                
                target_block = blocks[target_block_index]
                await target_block.scroll_into_view_if_needed()
                await asyncio.sleep(0.1)
                
                # Now grab the textarea inside this specific block
                ta = target_block.locator('textarea').first
                if await ta.count() > 0:
                    await ta.click(timeout=1000)
                    await target_page.keyboard.press("Control+A")
                    await target_page.keyboard.press("Backspace")
                    await target_page.keyboard.type(text, delay=10)
                    await target_page.keyboard.press("Escape")
                    
                    print(f"  [+] Filled Segment {index+1}/{len(segments)}: {text}")
                    filled += 1
                else:
                    print(f"  [!] Missing physical textbox layout for segment {index+1}.")
            except Exception as e:
                print(f"  [!] Failed applying text '{text}' on segment {index+1}: {e}")

        print(f"[✓] Automation complete! {filled}/{len(segments)} blocks filled and blurred.")

if __name__ == "__main__":
    asyncio.run(run())
