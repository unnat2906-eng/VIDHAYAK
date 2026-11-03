import asyncio
from playwright.async_api import async_playwright
import httpx

async def hybrid_instagram_automation(session_id: str, spam_text: str):
    # 1. Fast API Request for lightweight checks/session validation
    async with httpx.AsyncClient() as client:
        headers = {"Cookie": f"sessionid={session_id}", "User-Agent": "Instagram 219.0.0.12.117 Android"}
        res = await client.get("https://i.instagram.com/api/v1/accounts/current_user/", headers=headers)
        if res.status_code != 200:
            print("[ERROR] Invalid session via API")
            return

    # 2. Playwright for browser-level automation / rendering if needed
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        
        # Inject Instagram session cookie into browser
        await context.add_cookies([{
            "name": "sessionid",
            "value": session_id,
            "domain": ".instagram.com",
            "path": "/"
        }])
        
        page = await context.new_page()
        await page.goto("https://www.instagram.com/")
        
        print("[PLAYWRIGHT] Browser automation running successfully on Render!")
        await asyncio.sleep(5)
        await browser.close()
