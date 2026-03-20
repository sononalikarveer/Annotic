import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    print("\\n[Step 5] Creating Physical Segments on the Canvas...")
    
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
            
        print("CRITICAL INSTRUCTION: Ensure the Timeline Scale slider is zoomed completely OUT so segments don't overlap!")
        print("Waiting 5 seconds for visual confirmation...")
        await asyncio.sleep(5)
        
        rect = await target_page.locator('canvas').first.bounding_box()
        if not rect:
            print("Canvas not found!")
            return
            
        canvas_width = rect['width']
        canvas_x = rect['x']
        y_coord = rect['y'] + (rect['height'] / 2.0)
        
        # Audio length to configure pixels-per-second ratio
        total_duration = await target_page.evaluate("document.getElementById('audio-panel').duration")
        if not total_duration:
            print("Could not evaluate audio duration.")
            return
            
        pixels_per_second = canvas_width / total_duration
        print(f"Drawing bounds: {canvas_width}px over {total_duration}s -> Ratio: {pixels_per_second:.2f}px/sec")
        
        # Iteratively Shift-Drag original logic as requested by user
        prev_end_x = 0
        for index, seg in enumerate(segments):
            start_x = (seg['start'] * pixels_per_second) + canvas_x
            end_x = (seg['end'] * pixels_per_second) + canvas_x
            
            # Enforce exactly 2 pixels of physical spacing between the trailing edge and the new starting edge
            if index > 0 and start_x <= prev_end_x + 2:
                start_x = prev_end_x + 2
                
            prev_end_x = end_x
            
            print(f"-> Drawing Segment {index+1}/{len(segments)} at X:[{start_x:.1f} to {end_x:.1f}]")
            
            try:
                # Press Escape to guarantee any previously active DOM region is fully deselected
                await target_page.keyboard.press("Escape")
                await asyncio.sleep(0.05)
                
                await target_page.mouse.move(start_x, y_coord)
                await target_page.keyboard.down("Shift")
                
                await target_page.mouse.down()
                await asyncio.sleep(0.05)
                
                # Physical swipe to create the bounding region across the timeline
                await target_page.mouse.move(end_x, y_coord, steps=25)
                await asyncio.sleep(0.05)
                
                await target_page.mouse.up()
                await target_page.keyboard.up("Shift")
                
                # Wait for React to spawn the block on the right panel
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Failed drawing segment {index+1}: {e}")

        print("[✓] Finished converting all mathematical segments into visual blocks!")

if __name__ == "__main__":
    asyncio.run(run())
