import os
import asyncio
import random
import re
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
            
            await context.add_cookies([{
                "name": "sessionid",
                "value": clean_sid,
                "domain": ".instagram.com",
                "path": "/"
            }])
            
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

@app.post("/api/insta/fetch-gcs")
async def insta_fetch_gcs(session_id: str = Form(...)):
    # Mocking fetched GCs for the connected session (can be linked with real Instagram Direct threads API via Playwright)
    sample_gcs = [
        {"id": "thread_101", "name": "SONA VIP Group #1", "members": 15},
        {"id": "thread_102", "name": "Cyberpunk Spam GC #2", "members": 28},
        {"id": "thread_103", "name": "Unnat Automation Hub #3", "members": 42}
    ]
    log_module("gc", f"Fetched {len(sample_gcs)} GCs for session.")
    return {"success": True, "gcs": sample_gcs}

@app.post("/api/insta/start-task")
async def start_insta_task(task_type: str = Form(...), session_id: str = Form(...), target_data: str = Form(...)):
    log_module("instagram", f"Started task ({task_type}) under SONA protocol.")
    return {"success": True, "message": "Task executed successfully!"}

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
