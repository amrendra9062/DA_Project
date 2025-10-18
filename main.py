from fastapi import FastAPI, Request, Form, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import secrets
from typing import List

from database import SessionLocal, engine, Base
from models import User

# Create database tables
Base.metadata.create_all(bind=engine)

# FastAPI setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- ROUTES -----------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/check_email")
async def check_email(email: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return RedirectResponse(url=f"/login?email={email}", status_code=303)
    return RedirectResponse(url=f"/register?email={email}", status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, email: str = ""):
    return templates.TemplateResponse("register.html", {"request": request, "email": email})

@app.post("/register")
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    department: str = Form(...),
    bio: str = Form(...),
    interests: List[str] = Form(default=[]),
    db: Session = Depends(get_db)
):
    interests_str = ", ".join(interests)
    token = secrets.token_urlsafe(16)

    user = User(
        name=name,
        email=email,
        password=password,
        department=department,
        bio=bio,
        interests=interests_str,
        session_token=token
    )
    db.add(user)
    db.commit()

    response = RedirectResponse(url="/home", status_code=303)
    response.set_cookie(key="session_token", value=token, httponly=True)
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, email: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "email": email})

@app.post("/login")
async def login_user(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.password == password).first()
    if user:
        token = secrets.token_urlsafe(16)
        user.session_token = token
        db.commit()
        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(key="session_token", value=token, httponly=True)
        return response
    return HTMLResponse("Invalid credentials. <a href='/'>Try again</a>")

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not session_token:
        return RedirectResponse(url="/")
    user = db.query(User).filter(User.session_token == session_token).first()
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@app.post("/update_interests")
async def update_interests(interests: dict = {}, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    if not session_token:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    user = db.query(User).filter(User.session_token == session_token).first()
    if user:
        user.interests = ", ".join(interests.get("interests", []))
        db.commit()
    return JSONResponse({"status": "success"})

@app.get("/logout")
async def logout(session_token: str = Cookie(None), db: Session = Depends(get_db)):
    if session_token:
        user = db.query(User).filter(User.session_token == session_token).first()
        if user:
            user.session_token = None
            db.commit()
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")
    return response

