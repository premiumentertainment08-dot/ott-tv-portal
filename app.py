
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sqlite3, secrets, os, time

DB = Path(__file__).with_name("portal.db")
app = FastAPI(title="OTT TV Portal API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS content(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      kind TEXT NOT NULL DEFAULT 'movie',
      category TEXT DEFAULT 'Featured',
      description TEXT DEFAULT '',
      poster_url TEXT DEFAULT '',
      video_url TEXT DEFAULT '',
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS devices(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE NOT NULL,
      device_id TEXT DEFAULT '',
      name TEXT DEFAULT '',
      active INTEGER DEFAULT 0,
      created_at INTEGER NOT NULL
    );
    """)
    c.commit(); c.close()
init()

class ContentIn(BaseModel):
    title: str
    kind: str = "movie"
    category: str = "Featured"
    description: str = ""
    poster_url: str = ""
    video_url: str = ""

class ActivateIn(BaseModel):
    code: str
    device_id: str
    name: str = "TV"

def admin_guard(x_admin_key: str | None):
    key=os.getenv("ADMIN_KEY","change-me")
    if x_admin_key != key:
        raise HTTPException(401,"Invalid admin key")

@app.get("/")
def root():
    return {"name":"OTT TV Portal","status":"ok"}

@app.post("/admin/devices")
def create_device(x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    code=f"{secrets.randbelow(1000000):06d}"
    c=db()
    c.execute("INSERT INTO devices(code,created_at) VALUES(?,?)",(code,int(time.time())))
    c.commit(); c.close()
    return {"code":code}

@app.get("/admin/devices")
def devices(x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db(); rows=c.execute("SELECT * FROM devices ORDER BY id DESC").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/admin/devices/{device_id}/activate")
def approve_device(device_id:int,x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db(); c.execute("UPDATE devices SET active=1 WHERE id=?",(device_id,)); c.commit(); c.close()
    return {"ok":True}

@app.post("/admin/devices/{device_id}/deactivate")
def deactivate_device(device_id:int,x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db(); c.execute("UPDATE devices SET active=0 WHERE id=?",(device_id,)); c.commit(); c.close()
    return {"ok":True}

@app.post("/admin/content")
def add_content(item:ContentIn,x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db()
    cur=c.execute("""INSERT INTO content(title,kind,category,description,poster_url,video_url,created_at)
                     VALUES(?,?,?,?,?,?,?)""",
                  (item.title,item.kind,item.category,item.description,item.poster_url,item.video_url,int(time.time())))
    c.commit(); ident=cur.lastrowid; c.close()
    return {"id":ident,**item.model_dump()}

@app.get("/admin/content")
def all_content(x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db(); rows=c.execute("SELECT * FROM content ORDER BY id DESC").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.delete("/admin/content/{content_id}")
def delete_content(content_id:int,x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    c=db(); c.execute("DELETE FROM content WHERE id=?",(content_id,)); c.commit(); c.close()
    return {"ok":True}

@app.post("/admin/upload")
async def upload(file:UploadFile=File(...),x_admin_key: str | None = Header(default=None)):
    admin_guard(x_admin_key)
    # Local fallback. Replace with R2/S3 adapter in production.
    uploads=Path(__file__).with_name("uploads"); uploads.mkdir(exist_ok=True)
    safe=Path(file.filename or "upload.bin").name
    dest=uploads/safe
    with dest.open("wb") as f:
        while chunk:=await file.read(1024*1024):
            f.write(chunk)
    return {"filename":safe,"url":f"/uploads/{safe}","note":"Configure R2/S3 adapter for cloud storage."}

@app.post("/tv/activate")
def tv_activate(item:ActivateIn):
    c=db(); row=c.execute("SELECT * FROM devices WHERE code=?",(item.code,)).fetchone()
    if not row: c.close(); raise HTTPException(404,"Code not found")
    if not row["active"]:
        c.execute("UPDATE devices SET device_id=?,name=? WHERE id=?",(item.device_id,item.name,row["id"]))
        c.commit(); c.close()
        return {"status":"pending","message":"Waiting for admin approval"}
    c.execute("UPDATE devices SET device_id=?,name=? WHERE id=?",(item.device_id,item.name,row["id"]))
    c.commit(); c.close()
    token=secrets.token_urlsafe(32)
    return {"status":"active","token":token}

@app.get("/tv/content")
def tv_content(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"TV activation required")
    c=db(); rows=c.execute("SELECT * FROM content ORDER BY category,title").fetchall(); c.close()
    return [dict(r) for r in rows]
