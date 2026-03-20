import asyncio
from playwright.async_api import async_playwright

async def run():
    print("\\n[Step 2] Deleting Existing Blocks/Segments...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            target_page = None
            for context in browser.contexts:
                for page in context.pages:
                    if "annotic.in" in page.url:
                        target_page = page
                        break
                if target_page: break
            if not target_page:
                print("Could not find the Annotic page.")
                return
                
            cleared_count = 0
            while True:
                # Direct check for Trash icon if visible
                trash_btns = await target_page.locator('svg[data-icon="trash"]').all()
                if not trash_btns:
                    # Focus top block to reveal dynamic buttons
                    blocks = await target_page.locator('div[id^="sub_"]').all()
                    if blocks:
                        try:
                            await blocks[0].scroll_into_view_if_needed()
                            await blocks[0].click(timeout=1000)
                            await asyncio.sleep(0.3)
                        except: pass
                    else:
                        break # Canvas is completely empty!
                        
                # Re-fetch after hover
                trash_btns = await target_page.locator('svg[data-icon="trash"]').all()
                if trash_btns:
                    try:
                        await trash_btns[0].locator('..').click(timeout=1000)
                        cleared_count += 1
                        await asyncio.sleep(0.3)
                    except: break
                else: break

            print(f"[✓] Canvas cleared. Deleted {cleared_count} components.")
            
        except Exception as e:
            print(f"Failed to clear canvas: {e}")

if __name__ == "__main__":
    asyncio.run(run())
