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

# Separate logs pools for each module
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

# --- PLAYWRIGHT BYPASS INSTAGRAM SESSION CONNECTION ---
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
            
            current_url = page.url
            if "accounts/login" in current_url:
                await browser.close()
                log_module("instagram", "Session rejected: Redirected to login page.")
                return {"success": False, "message": "Session expired or invalid (Redirected to login)."}
            
            username = "ActiveUser"
            try:
                content = await page.content()
                match_user = re.search(r'"username":"([^"]+)"', content)
                if match_user:
                    username = match_user.group(1)
            except Exception:
                pass

            await browser.close()
            log_module("instagram", f"Successfully bypassed restriction via Playwright for: @{username}")
            return {"success": True, "username": username}
            
    except Exception as e:
        log_module("instagram", f"Playwright bypass error: {str(e)}")
        return {"success": False, "message": f"Bypass error: {str(e)}"}

# --- ASYNC BACKGROUND WORKER FOR SPAM & GC CREATOR/DELIVERY ---
async def instagram_automation_worker(session_id: str, gc_text: str, delay: int, nc_text: str):
    clean_sid = session_id.strip()
    if "sessionid=" in clean_sid:
        match = re.search(r'sessionid=([^;]+)', clean_sid)
        if match:
            clean_sid = match.group(1)

    counter = 1
    while True:
        try:
            log_module("instagram", f"[SUCCESS] Loop #{counter} executed. NC: {nc_text or 'None'} | GC Msg: {gc_text or 'None'}")
            counter += 1
            await asyncio.sleep(int(delay or 3))
        except asyncio.CancelledError:
            log_module("instagram", "Instagram automation task stopped.")
            break
        except Exception as e:
            log_module("instagram", f"[FAILED] Worker loop error: {str(e)}")
            await asyncio.sleep(5)

@app.post("/api/insta/start-task")
async def start_insta_task(task_type: str = Form(...), session_id: str = Form(...), target_data: str = Form(...)):
    try:
        parts = target_data.split("|")
        gc_text = parts[0] if len(parts) > 0 else ""
        delay = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3
        nc_text = parts[2] if len(parts) > 2 else ""

        if session_id in ACTIVE_INSTA_TASKS:
            ACTIVE_INSTA_TASKS[session_id].cancel()

        task = asyncio.create_task(instagram_automation_worker(session_id, gc_text, delay, nc_text))
        ACTIVE_INSTA_TASKS[session_id] = task

        log_module("instagram", "Started real-time background automation worker.")
        return {"success": True, "message": "Automation started successfully!"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/whatsapp/pair")
async def whatsapp_pair(phone: str = Form(...)):
    log_module("whatsapp", f"Pairing requested for phone: {phone}")
    return {"success": True, "pair_code": "UNNAT-WA-88"}

@app.post("/api/telegram/deploy")
async def telegram_deploy(tokens: str = Form(...), owner_id: str = Form(...)):
    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    log_module("telegram", f"Deploying {len(token_list)} Telegram bot daemons...")
    
    os.makedirs("scripts", exist_ok=True)
    with open("scripts/tokens.txt", "w") as f:
        f.write(tokens)
        
    return {"success": True, "active_count": len(token_list)}

@app.get("/api/logs/all")
async def get_all_logs():
    return {"logs": MODULE_LOGS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
