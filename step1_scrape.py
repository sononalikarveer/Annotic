import asyncio
import requests
from urllib.parse import urljoin
from playwright.async_api import async_playwright

async def run():
    print("\\n[Step 1] Scraping content from Annotic...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("Failed to connect to Google Chrome via port 9222. Is it running?")
            return
            
        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "annotic.in" in page.url:
                    target_page = page
                    break
            if target_page: break
            
        if not target_page:
            print("Could not find the Annotic page opened in the browser.")
            return
            
        print(f"Attached to page: {target_page.url}")
        
        # 1. Download Audio
        try:
            audio_element = await target_page.wait_for_selector('audio', timeout=5000)
            src = await audio_element.get_attribute('src')
            if src and src.startswith('/'):
                src = urljoin(target_page.url, src)
                
            print(f"Downloading audio from {src}...")
            r = requests.get(src, stream=True)
            r.raise_for_status()
            with open("target_audio.mp3", 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print("[✓] Saved as target_audio.mp3")
        except Exception as e:
            print(f"Could not download audio: {e}")

if __name__ == "__main__":
    asyncio.run(run())
