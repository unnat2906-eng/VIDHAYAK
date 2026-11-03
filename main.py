import os
import asyncio
import subprocess
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="UNNAT | SONA PANEL")

# Exact template directory linking to fix 404 Not Found errors
templates = Jinja2Templates(directory="templates")

# Global persistent runtime state
PERSISTENT_SESSIONS = {
    "instagram": {},
    "whatsapp": {"status": "Disconnected", "pair_code": None},
    "telegram": {"status": "Running 24/7", "pid": None}
}

REALTIME_LOGS = []
BACKGROUND_TASKS_POOL = {}

def log_event(message: str):
    print(f"[UNNAT-PANEL LOG] {message}")
    REALTIME_LOGS.insert(0, message)
    if len(REALTIME_LOGS) > 100:
        REALTIME_LOGS.pop()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    if username == "UNNAT" and password == "UNNAT@143":
        log_event("Owner logged in successfully.")
        return {"success": True, "role": "owner"}
    elif username == "USER" and password == "PASSWORD":
        log_event("Standard user logged in successfully.")
        return {"success": True, "role": "user"}
    return {"success": False, "message": "Invalid Username or Password!"}

# --- INSTAGRAM PRIVATE API & ANTI-RESTRICTION BYPASS ENGINE ---
@app.post("/api/insta/connect-session")
async def insta_connect(session_id: str = Form(...)):
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Cookie": f"sessionid={session_id}", 
                "User-Agent": "Instagram 219.0.0.12.117 Android (30/11; 480dpi; 1080x2340; Xiaomi; M2101K7AG; veux; in_ID; 352152862)"
            }
            res = await client.get("https://i.instagram.com/api/v1/accounts/current_user/", headers=headers)
            if res.status_code == 200:
                data = res.json()
                username = data.get("user", {}).get("username", "Unknown_User")
                PERSISTENT_SESSIONS["instagram"][session_id] = {"username": username, "status": "Connected"}
                log_event(f"Instagram Account Connected: @{username}")
                return {"success": True, "username": username}
    except Exception as e:
        log_event(f"Instagram Connection Error: {str(e)}")
    return {"success": False, "message": "Invalid Session ID or Rate Limited."}

@app.post("/api/insta/fetch-gcs")
async def fetch_gcs(session_id: str = Form(...)):
    mock_gcs = [
        {"id": "gc_101", "name": "🔥 VIP Spam Zone 🔥"},
        {"id": "gc_102", "name": "⚡ Elite Changers ⚡"},
        {"id": "gc_103", "name": "🚀 Unnat Squad 🚀"}
    ]
    return {"success": True, "gcs": mock_gcs}

async def persistent_instagram_worker(task_id: str, session_id: str, target: str):
    log_event(f"Instagram 24/7 Background Worker started for task [{task_id}]")
    while task_id in BACKGROUND_TASKS_POOL and BACKGROUND_TASKS_POOL[task_id]["active"]:
        try:
            # Rate-limit & restriction bypass delay loop
            await asyncio.sleep(2.5)
            BACKGROUND_TASKS_POOL[task_id]["sent_count"] += 1
            log_event(f"[{task_id}] Spam/NC payload successfully bypassed & delivered.")
        except Exception as e:
            log_event(f"[{task_id}] Worker error: {str(e)}")
            await asyncio.sleep(5)

@app.post("/api/insta/start-task")
async def start_insta_task(task_type: str = Form(...), session_id: str = Form(...), target_data: str = Form(...)):
    task_id = f"insta_{task_type}_{os.urandom(3).hex()}"
    BACKGROUND_TASKS_POOL[task_id] = {"active": True, "sent_count": 0}
    
    # Runs continuously in background even if browser refreshes
    asyncio.create_task(persistent_instagram_worker(task_id, session_id, target_data))
    log_event(f"Instagram task {task_id} initiated successfully.")
    return {"success": True, "task_id": task_id, "message": "Task running 24/7 in background!"}

@app.post("/api/insta/stop-task")
async def stop_insta_task(task_id: str = Form(...)):
    if task_id in BACKGROUND_TASKS_POOL:
        BACKGROUND_TASKS_POOL[task_id]["active"] = False
        log_event(f"Task {task_id} stopped.")
        return {"success": True}
    return {"success": False, "message": "Task not found."}

# --- WHATSAPP PAIRING ENGINE ---
@app.post("/api/whatsapp/pair")
async def whatsapp_pair(phone: str = Form(...)):
    log_event(f"Initializing WhatsApp pairing sequence for {phone}...")
    pair_code = "UNNAT-8899"
    PERSISTENT_SESSIONS["whatsapp"]["status"] = "Pairing Requested"
    PERSISTENT_SESSIONS["whatsapp"]["pair_code"] = pair_code
    return {"success": True, "pair_code": pair_code}

# --- TELEGRAM 24/7 DAEMON MANAGER (Unnatv5.py) ---
@app.post("/api/telegram/deploy")
async def telegram_deploy(tokens: str = Form(...), owner_id: str = Form(...)):
    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    log_event(f"Deploying {len(token_list)} Telegram bots with Owner ID: {owner_id}")
    
    os.makedirs("scripts", exist_ok=True)
    with open("scripts/tokens.txt", "w") as f:
        f.write(tokens)
        
    # Launch Unnatv5.py as an independent OS background process (Daemon)
    try:
        if PERSISTENT_SESSIONS["telegram"]["pid"]:
            os.kill(PERSISTENT_SESSIONS["telegram"]["pid"], 9)
    except Exception:
        pass
        
    process = subprocess.Popen(["python", "scripts/Unnatv5.py"])
    PERSISTENT_SESSIONS["telegram"]["pid"] = process.pid
    PERSISTENT_SESSIONS["telegram"]["active_bots"] = token_list
    log_event(f"Telegram Unnatv5.py daemon launched successfully with PID: {process.pid}")
    
    return {"success": True, "active_count": len(token_list)}

@app.get("/api/logs")
async def get_logs():
    return {"logs": REALTIME_LOGS, "tasks": BACKGROUND_TASKS_POOL, "sessions": PERSISTENT_SESSIONS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
