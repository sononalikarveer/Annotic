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
                blocks = await target_page.locator('div[id^="sub_"]').all()
                if len(blocks) == 0:
                    break
                    
                deleted_in_pass = False
                
                # Iterate backward to safely delete from the bottom up without shifting DOM indexes
                for block in reversed(blocks):
                    try:
                        await block.scroll_into_view_if_needed()
                        await block.click(timeout=1000)
                        await asyncio.sleep(0.2)
                        
                        # Now that it's focused, grab the Trash button specific to this block
                        trash = block.locator('button[aria-label*="Delete" i]').first
                        if await trash.count() > 0:
                            await block.hover() # Hover to reveal the button if it's hidden
                            await trash.click(timeout=1000, force=True)
                            cleared_count += 1
                            deleted_in_pass = True
                            await asyncio.sleep(0.5)
                            break # Break the for loop to re-fetch the clean DOM in the while loop
                    except Exception as e:
                        pass
                        
                if not deleted_in_pass:
                    # If we made a full pass and deleted nothing, stop immediately to prevent infinite loops
                    break

            print(f"[✓] Canvas cleared. Deleted {cleared_count} components.")
            
        except Exception as e:
            print(f"Failed to clear canvas: {e}")

if __name__ == "__main__":
    asyncio.run(run())
