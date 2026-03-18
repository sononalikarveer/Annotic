import asyncio
from playwright.async_api import async_playwright
import time

async def get_html():
    async with async_playwright() as p:
        try:
            print("Connecting to Chrome on 9222...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("Connected!")
            
            # Find the annotic.in page
            contexts = browser.contexts
            target_page = None
            
            # Give it a second to load contexts
            await asyncio.sleep(1)
            
            for context in contexts:
                for page in context.pages:
                    url = page.url
                    print(f"- Found open tab: {url}")
                    if "annotic.in" in url:
                        target_page = page
            
            if target_page:
                print(f"\\nFound target page! URL: {target_page.url}")
                # Get the HTML body
                body_html = await target_page.evaluate("document.body.outerHTML")
                
                # Save to a file to inspect
                with open("annotic_body.html", "w", encoding="utf-8") as f:
                    f.write(body_html)
                print("Saved body HTML to annotic_body.html")
                
                # Try to find audio tags specifically
                audio_tags = await target_page.evaluate('''() => {
                    const audios = document.querySelectorAll('audio, video');
                    return Array.from(audios).map(a => `<${a.tagName.toLowerCase()} src="${a.src}">`);
                }''')
                print(f"\\nFound media tags: {audio_tags}")
                
            else:
                print("Could not find an annotic.in tab open in this browser.")
                
            await browser.close()
        except Exception as e:
            print(f"Error connecting: {e}")

if __name__ == "__main__":
    asyncio.run(get_html())
