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
            
        print("Will attempt to keep Timeline Scale at minimum for every segment...")
        
        prev_end_time_sec = -9999.0
        for index, seg in enumerate(segments):
            # 1. Reset timeline scale to prevent auto-zoom drift using native mouse click on the left edge of the slider
            try:
                sliders = target_page.locator('input[type="range"]')
                if await sliders.count() > 0:
                    first_slider = sliders.first
                    await first_slider.scroll_into_view_if_needed()
                    # Click 2 pixels from the left edge of the slider bounding box to force 'min' zoom
                    await first_slider.click(position={"x": 2, "y": 2}, force=True)
            except Exception as e:
                print(f"Slider reset failed: {e}")
            
            # Wait a moment for UI to settle the zoom level
            await asyncio.sleep(0.5)
            
            # 2. Recalculate coordinates per segment dynamically
            rect = await target_page.locator('canvas').first.bounding_box()
            if not rect:
                print("Canvas not found! Skipping...")
                continue
                
            canvas_width = rect['width']
            canvas_x = rect['x']
            y_coord = rect['y'] + (rect['height'] / 2.0)
            
            total_duration = await target_page.evaluate("document.getElementById('audio-panel').duration")
            if not total_duration:
                print("Could not get audio duration.")
                continue
                
            pixels_per_second = canvas_width / total_duration
            gap_seconds = 4.0 / pixels_per_second
            
            # 3. Enforce 4-pixel gap/width in time-domain so scrolling doesn't corrupt it
            start_time = max(seg['start'], prev_end_time_sec + gap_seconds)
            end_time = max(seg['end'], start_time + gap_seconds)
            
            prev_end_time_sec = end_time
            
            start_x = (start_time * pixels_per_second) + canvas_x
            end_x = (end_time * pixels_per_second) + canvas_x
            
            print(f"-> Drawing Segment {index+1}/{len(segments)} from {start_time:.2f}s to {end_time:.2f}s (X:[{start_x:.1f} to {end_x:.1f}])")
            
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
