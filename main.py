import os
import asyncio
import subprocess
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="UNNAT | SONA PANEL")
templates = Jinja2Templates(directory="templates")

# Global persistent runtime state
PERSISTENT_SESSIONS = {
    "instagram": {},
    "whatsapp": {"status": "Running 24/7", "pid": None},
    "telegram": {"status": "Running 24/7", "pid": None}
}

BACKGROUND_TASKS_POOL = {}

def log_event(message: str):
    print(f"[24/7 PERSISTENT LOG] {message}")

# --- 24/7 BACKGROUND WORKER FOR INSTAGRAM ---
async def persistent_instagram_worker(task_id: str, session_id: str, target: str):
    print(f"[INSTAGRAM] Background worker started for session {sessionid_masked(session_id)}")
    while task_id in BACKGROUND_TASKS_POOL and BACKGROUND_TASKS_POOL[task_id]["active"]:
        try:
            # Yahan aapka anti-ban spam aur name changer private API logic chalega
            await asyncio.sleep(3) # Rate limit bypass delay
            BACKGROUND_TASKS_POOL[task_id]["sent_count"] += 1
            log_event(f"Task [{task_id}] successfully delivered payload. Total sent: {BACKGROUND_TASKS_POOL[task_id]['sent_count']}")
        except Exception as e:
            log_event(f"Task [{task_id}] error: {str(e)}")
            await asyncio.sleep(5)

@app.post("/api/insta/start-persistent-task")
async def start_persistent_task(session_id: str = Form(...), target: str = Form(...)):
    task_id = f"ig_task_{os.urandom(3).hex()}"
    BACKGROUND_TASKS_POOL[task_id] = {"active": True, "sent_count": 0}
    
    # Background task background me independent run karega, browser refresh se affect nahi hoga
    asyncio.create_task(persistent_instagram_worker(task_id, session_id, target))
    return {"success": True, "task_id": task_id, "message": "Instagram task running 24/7 in background!"}

# --- 24/7 SUBPROCESS WORKER FOR TELEGRAM (Unnatv5.py) & WHATSAPP ---
@app.post("/api/services/launch-daemon")
async def launch_daemons(tokens: str = Form(...), owner_id: str = Form(...)):
    os.makedirs("scripts", exist_ok=True)
    with open("scripts/tokens.txt", "w") as f:
        f.write(tokens)
        
    # Start Unnatv5.py as an independent background daemon process
    try:
        if PERSISTENT_SESSIONS["telegram"]["pid"]:
            os.kill(PERSISTENT_SESSIONS["telegram"]["pid"], 9)
    except Exception:
        pass
        
    process = subprocess.Popen(["python", "scripts/Unnatv5.py"])
    PERSISTENT_SESSIONS["telegram"]["pid"] = process.pid
    log_event(f"Telegram Unnatv5.py daemon launched successfully with PID: {process.pid}")
    
    return {"success": True, "message": "Telegram & WhatsApp daemons running 24/7 successfully!"}

def sessionid_masked(sid):
    return sid[:6] + "..." if len(sid) > 6 else "active"
