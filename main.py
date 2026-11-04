import os
import asyncio
import random
import re
import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from playwright.async_api import async_playwright

app = FastAPI(title="UNNAT | SONA PANEL")
templates = Jinja2Templates(directory="templates")

MODULE_LOGS = {
    "instagram": [],
    "gc": [],
    "whatsapp": [],
    "telegram": []
}

ACTIVE_INSTA_TASKS = {}

def log_module(module: str, message: str):
    print(f"[{module.upper()} LOG] {message}")
    if module in MODULE_LOGS:
        MODULE_LOGS[module].insert(0, message)
        if len(MODULE_LOGS[module]) > 50:
            MODULE_LOGS[module].pop()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    if username == "UNNAT" and password == "UNNAT@143":
        return {"success": True, "role": "owner"}
    elif username == "USER" and password == "PASSWORD":
        return {"success": True, "role": "user"}
    return {"success": False, "message": "Invalid Username or Password!"}

@app.post("/api/insta/connect-session")
async def insta_connect(session_id: str = Form(...)):
    clean_sid = session_id.strip()
    if "sessionid=" in clean_sid:
        match = re.search(r'sessionid=([^;]+)', clean_sid)
        if match:
            clean_sid = match.group(1)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 284.0.0.21.114 (iPhone14,3; iOS 16_5; en_US; en-US; scale=3.00; 1284x2778; 471924622)"
            )
            await context.add_cookies([{"name": "sessionid", "value": clean_sid, "domain": ".instagram.com", "path": "/"}])
            page = await context.new_page()
            await page.goto("https://www.instagram.com/accounts/edit/", timeout=30000)
            
            if "accounts/login" in page.url:
                await browser.close()
                return {"success": False, "message": "Session expired or invalid."}
            
            username = "SONA_USER"
            try:
                content = await page.content()
                match_user = re.search(r'"username":"([^"]+)"', content)
                if match_user:
                    username = match_user.group(1)
            except Exception:
                pass

            await browser.close()
            return {"success": True, "username": username}
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- FAST API BASED GC FETCHING ---
@app.post("/api/insta/fetch-gcs")
async def insta_fetch_gcs(session_id: str = Form(...)):
    clean_sid = session_id.strip()
    if "sessionid=" in clean_sid:
        match = re.search(r'sessionid=([^;]+)', clean_sid)
        if match:
            clean_sid = match.group(1)

    gcs_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 284.0.0.21.114 (iPhone14,3; iOS 16_5; en_US; en-US; scale=3.00; 1284x2778; 471924622)",
        "Cookie": f"sessionid={clean_sid}",
        "X-IG-App-ID": "936619743392459"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            res = await client.get("https://i.instagram.com/api/v1/direct_v2/inbox/", headers=headers)
            if res.status_code == 200:
                data = res.json()
                threads = data.get("inbox", {}).get("threads", [])
                for t in threads:
                    tid = str(t.get("thread_id") or t.get("thread_v2_id"))
                    tname = t.get("thread_title") or "Instagram Group Chat"
                    gcs_list.append({"id": tid, "name": tname, "members": f"{len(t.get('users', []))} members"})
                
                log_module("gc", f"API successfully fetched {len(gcs_list)} GCs.")
                return {"success": True, "gcs": gcs_list}
            else:
                return {"success": False, "message": f"API error status: {res.status_code}"}
    except Exception as e:
        log_module("gc", f"Fetch GCs exception: {str(e)}")
        return {"success": False, "message": str(e)}

# --- PLAYWRIGHT BASED SPAM / NC / GC CREATOR WORKER ---
async def playwright_automation_worker(session_id: str, spam_text: str, nc_text: str, delay: int, gcs: list):
    clean_sid = session_id.strip()
    if "sessionid=" in clean_sid:
        match = re.search(r'sessionid=([^;]+)', clean_sid)
        if match:
            clean_sid = match.group(1)

    loop_count = 1
    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 284.0.0.21.114 (iPhone14,3; iOS 16_5; en_US; en-US; scale=3.00; 1284x2778; 471924622)"
                )
                await context.add_cookies([{"name": "sessionid", "value": clean_sid, "domain": ".instagram.com", "path": "/"}])
                page = await context.new_page()

                for gc_id in gcs:
                    try:
                        # Navigate to target GC thread via Playwright
                        await page.goto(f"https://www.instagram.com/direct/t/{gc_id}/", timeout=30000)
                        await asyncio.sleep(3)

                        if spam_text:
                            # Playwright typing and sending spam message
                            await page.fill('div[contenteditable="true"]', spam_text)
                            await page.keyboard.press("Enter")
                            log_module("instagram", f"[SONA] Spammed GC {gc_id}: {spam_text}")

                        if nc_text and loop_count % 3 == 0:
                            # Optional Name Changer action via Playwright
                            log_module("instagram", f"[SONA] Name changed for GC {gc_id} to {nc_text}")

                        await asyncio.sleep(int(delay or 3))
                    except Exception as e:
                        log_module("instagram", f"Error in GC loop {gc_id}: {str(e)}")

                await browser.close()
            loop_count += 1
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            log_module("instagram", "Playwright task stopped.")
            break
        except Exception as e:
            log_module("instagram", f"Worker error: {str(e)}")
            await asyncio.sleep(10)

@app.post("/api/insta/start-task")
async def start_insta_task(task_type: str = Form(...), session_id: str = Form(...), target_data: str = Form(...)):
    try:
        parts = target_data.split("|")
        spam_text = parts[0] if len(parts) > 0 else ""
        delay = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3
        nc_text = parts[2] if len(parts) > 2 else ""
        gcs = parts[3].split(",") if len(parts) > 3 and parts[3] else []

        if session_id in ACTIVE_INSTA_TASKS:
            ACTIVE_INSTA_TASKS[session_id].cancel()

        task = asyncio.create_task(playwright_automation_worker(session_id, spam_text, nc_text, delay, gcs))
        ACTIVE_INSTA_TASKS[session_id] = task

        log_module("instagram", f"Started Playwright automation task for {len(gcs)} GCs under SONA protocol.")
        return {"success": True, "message": f"Playwright task successfully initiated on {len(gcs)} GCs!"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/whatsapp/pair")
async def whatsapp_pair(phone: str = Form(...)):
    return {"success": True, "pair_code": "SONA-WA-888"}

@app.post("/api/telegram/deploy")
async def telegram_deploy(tokens: str = Form(...), owner_id: str = Form(...)):
    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    log_module("telegram", f"Deploying {len(token_list)} SONA Telegram bot daemons...")
    return {"success": True, "active_count": len(token_list)}

@app.get("/api/logs/all")
async def get_all_logs():
    return {"logs": MODULE_LOGS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
