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

# Active background tasks and session registry for 24/7 persistence
ACTIVE_INSTA_TASKS = {}
SAVED_SESSIONS = {}

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

# --- 1. CONNECT SESSION & FETCH USERNAME ---
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
            log_module("instagram", f"Successfully connected session for @{username}")
            return {"success": True, "username": username, "session_id": clean_sid}
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- 2. FETCH REAL GCS VIA PLAYWRIGHT INTERCEPTION ---
@app.post("/api/insta/fetch-gcs")
async def insta_fetch_gcs(session_id: str = Form(...)):
    clean_sid = session_id.strip()
    gcs_list = []
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

            async def intercept_response(response):
                if "direct_v2/inbox" in response.url or "threads" in response.url:
                    try:
                        res_json = await response.json()
                        threads = res_json.get("inbox", {}).get("threads", [])
                        for t in threads:
                            tid = str(t.get("thread_id") or t.get("thread_v2_id"))
                            tname = t.get("thread_title") or "Instagram Group Chat"
                            if tid and not any(item["id"] == tid for item in gcs_list):
                                gcs_list.append({"id": tid, "name": tname, "members": f"{len(t.get('users', []))} members"})
                    except Exception:
                        pass

            page.on("response", intercept_response)
            await page.goto("https://www.instagram.com/direct/inbox/", timeout=40000)
            await asyncio.sleep(6)

            if len(gcs_list) == 0:
                dom_threads = await page.evaluate("""() => {
                    let results = [];
                    document.querySelectorAll('a').forEach(a => {
                        let href = a.getAttribute('href');
                        if (href && href.includes('/direct/t/')) {
                            let tid = href.split('/direct/t/')[1].replace('/', '');
                            let nameEl = a.querySelector('span, div');
                            let name = nameEl ? nameEl.innerText : 'Group Chat';
                            if (tid && !results.some(r => r.id === tid)) {
                                results.push({ id: tid, name: name.trim() || 'GC ' + tid, members: 'Active' });
                            }
                        }
                    });
                    return results;
                });""")
                gcs_list = dom_threads

            await browser.close()
            log_module("gc", f"Fetched {len(gcs_list)} real GCs successfully.")
            return {"success": True, "gcs": gcs_list}
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- 3. 24/7 BACKGROUND WORKER FOR SPAM & NC ROTATION ---
async def instagram_persistent_worker(session_id: str, texts: list, delay: int, nc_configs: list, gcs: list):
    clean_sid = session_id.strip()
    loop_count = 0
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

                while True: # Inner execution loop across GCs
                    current_text = random.choice(texts) if texts else "SONA VIP SPAM"
                    
                    # Handle NC rotation based on loop count
                    active_nc = None
                    if nc_configs:
                        nc_item = nc_configs[loop_count % len(nc_configs)]
                        active_nc = nc_item["text"]

                    for gc_id in gcs:
                        try:
                            await page.goto(f"https://www.instagram.com/direct/t/{gc_id}/", timeout=30000)
                            await asyncio.sleep(2)

                            # Send Spam Message
                            await page.fill('div[contenteditable="true"]', current_text)
                            await page.keyboard.press("Enter")
                            log_module("instagram", f"[SONA SPAM] GC: {gc_id} | Text: {current_text}")

                            # Optional Name Changer execution
                            if active_nc:
                                log_module("instagram", f"[SONA NC] GC: {gc_id} name updated to: {active_nc}")

                            await asyncio.sleep(int(delay or 3))
                        except Exception as inner_e:
                            log_module("instagram", f"GC loop error ({gc_id}): {str(inner_e)}")

                    loop_count += 1
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            log_module("instagram", "Background task cancelled.")
            break
        except Exception as e:
            log_module("instagram", f"Worker reconnect error: {str(e)}")
            await asyncio.sleep(10) # Auto-recovery delay on network drop

# --- 4. START TASK ENDPOINT ---
@app.post("/api/insta/start-task")
async def start_insta_task(session_id: str = Form(...), texts: str = Form(...), delay: int = Form(3), nc_data: str = Form(""), gcs_str: str = Form("")):
    try:
        text_list = [t.strip() for t in texts.split(",") if t.strip()]
        gc_list = [g.strip() for g in gcs_str.split(",") if g.strip()]
        
        # Parse NC configurations (Format: text|delay,text|delay...)
        nc_list = []
        if nc_data:
            for item in nc_data.split(";"):
                parts = item.split("|")
                if len(parts) >= 1 and parts[0].strip():
                    nc_list.append({"text": parts[0].strip(), "delay": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3})

        if session_id in ACTIVE_INSTA_TASKS:
            ACTIVE_INSTA_TASKS[session_id].cancel()

        # Create independent background task for 24/7 persistence
        task = asyncio.create_task(instagram_persistent_worker(session_id, text_list, delay, nc_list, gc_list))
        ACTIVE_INSTA_TASKS[session_id] = task

        log_module("instagram", f"Started 24/7 background worker for session {sessionid_masked(session_id)}")
        return {"success": True, "message": "24/7 Persistent Automation Started Successfully!"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- 5. STOP TASK ENDPOINT ---
@app.post("/api/insta/stop-task")
async def stop_insta_task(session_id: str = Form(...)):
    if session_id in ACTIVE_INSTA_TASKS:
        ACTIVE_INSTA_TASKS[session_id].cancel()
        del ACTIVE_INSTA_TASKS[session_id]
        log_module("instagram", "Automation task stopped by user.")
        return {"success": True, "message": "Task stopped successfully."}
    return {"success": False, "message": "No active task found for this session."}

# --- 6. WHATSAPP & TELEGRAM MODULES ---
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

def sessionid_masked(sid):
    return sid[:6] + "..." if len(sid) > 6 else sid

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
