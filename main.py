from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/check_email")
async def check_email(request: Request, email: str = Form(...)):
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if existing:
        return RedirectResponse(url=f"/login?email={email}", status_code=303)
    return RedirectResponse(url=f"/register?email={email}", status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, email: str):
    return templates.TemplateResponse("register.html", {"request": request, "email": email})

@app.post("/register")
async def register_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    department: str = Form(...),
    bio: str = Form(...),
    interests: str = Form(...)
):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO users (name, email, password, department, bio, interests) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password, department, bio, interests)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/home?email={email}", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, email: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "email": email})

@app.post("/login")
async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
    conn.close()
    if user:
        return RedirectResponse(url=f"/home?email={email}", status_code=303)
    return HTMLResponse("Invalid credentials. <a href='/'>Try again</a>")

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, email: str):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@app.post("/add_interest")
async def add_interest(email: str = Form(...), new_interest: str = Form(...)):
    conn = get_db_connection()
    user = conn.execute("SELECT interests FROM users WHERE email=?", (email,)).fetchone()
    if user:
        current = user["interests"] or ""
        updated = (current + ", " + new_interest) if current else new_interest
        conn.execute("UPDATE users SET interests=? WHERE email=?", (updated, email))
        conn.commit()
    conn.close()
    return RedirectResponse(url=f"/home?email={email}", status_code=303)

