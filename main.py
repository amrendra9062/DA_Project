from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
from fastapi import FastAPI, Request, Form, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
import secrets
from typing import List

from database import SessionLocal, engine, Base
from models import User, Message


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()

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

#Added by Utkarsh(to get users list)
@app.get("/users", response_class=HTMLResponse)
async def get_users_list(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Displays a list of all users to chat with."""
    if not session_token:
        return RedirectResponse(url="/")
        
    current_user = db.query(User).filter(User.session_token == session_token).first()
    if not current_user:
        return RedirectResponse(url="/")

    # Fetch all users except the current one
    all_users = db.query(User).filter(User.id != current_user.id).all()
    
    return templates.TemplateResponse("users.html", {"request": request, "users": all_users})

@app.get("/search", response_class=HTMLResponse)
async def search_users(
    request: Request,
    q: str = "",
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Search for users based on interests or name."""
    if not session_token:
        return RedirectResponse(url="/")

    current_user = db.query(User).filter(User.session_token == session_token).first()
    if not current_user:
        return RedirectResponse(url="/")

    if not q.strip():
        results = []
    else:
        # Search by name or interests (case-insensitive)
        results = db.query(User).filter(
            User.id != current_user.id,
            or_(
                User.name.ilike(f"%{q}%"),
                User.interests.ilike(f"%{q}%")
            )
        ).all()

    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "user": current_user,
            "query": q,
            "results": results
        }
    )


#Added by Utkarsh (Route for chat)
@app.get("/chat/{receiver_id}", response_class=HTMLResponse)
async def get_chat_page(
    request: Request,
    receiver_id: int,
    session_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Serves the chat page for a specific conversation."""
    if not session_token:
        return RedirectResponse(url="/")

    # Get the current user (sender)
    current_user = db.query(User).filter(User.session_token == session_token).first()
    if not current_user:
        return RedirectResponse(url="/")

    # Get the user they want to chat with (receiver)
    receiver_user = db.query(User).filter(User.id == receiver_id).first()
    if not receiver_user:
        return HTMLResponse("User not found.", status_code=404)

    # Load the message history between the two users
    message_history = db.query(Message).filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == receiver_id),
            (Message.sender_id == receiver_id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "current_user": current_user,
            "receiver": receiver_user,
            "message_history": message_history
        }
    )
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

#Added by Utkarsh(websocket for chatting feature)
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            sender_id = data['sender_id']
            receiver_id = data['receiver_id']
            message_content = data['content']
            
            #uncomment only the line bwlow to see that messages are being received.
            # print(f"INFO:     Message received for user {receiver_id}. Content: {message_content}")
            # Save message to the database
            db_message = Message(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=message_content
            )
            db.add(db_message)
            db.commit()

            # Send message to the receiver if they are connected
            await manager.send_personal_message(message_content, receiver_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)

