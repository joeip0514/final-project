from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, and_
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import os
from werkzeug.utils import secure_filename

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler to match Flask's error format
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'error': exc.detail, 'success': False}
    )

# Security
SECRET_KEY = 'your-secret-key-change-in-production'
ALGORITHM = 'HS256'
# 支持多種哈希格式以兼容舊的 werkzeug 哈希
pwd_context = CryptContext(
    schemes=["bcrypt", "pbkdf2_sha256"], 
    deprecated="auto",
    pbkdf2_sha256__default_rounds=260000  # werkzeug 默認值
)

# Database
DATABASE_URL = 'sqlite:///./instance/project_delegation.db'
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Templates and Static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("instance", exist_ok=True)

# Database Models
class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'delegator' or 'recipient'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    delegated_projects = relationship('Project', foreign_keys='Project.delegator_id', back_populates='delegator')
    received_projects = relationship('Project', foreign_keys='Project.delegate_id', back_populates='delegate')
    quotes = relationship('Quote', back_populates='recipient')
    sent_messages = relationship('Message', foreign_keys='Message.sender_id', back_populates='sender')
    received_messages = relationship('Message', foreign_keys='Message.receiver_id', back_populates='receiver')
    uploaded_files = relationship('ClosureFile', back_populates='uploader')

class Project(Base):
    __tablename__ = 'project'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='pending')  # pending, active, completed, closed
    delegator_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    delegate_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    delegator = relationship('User', foreign_keys=[delegator_id], back_populates='delegated_projects')
    delegate = relationship('User', foreign_keys=[delegate_id], back_populates='received_projects')
    quotes = relationship('Quote', back_populates='project')
    messages = relationship('Message', back_populates='project')
    closure_files = relationship('ClosureFile', back_populates='project')

class Quote(Base):
    __tablename__ = 'quote'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    amount = Column(Float, nullable=False)
    message = Column(Text)
    status = Column(String(20), default='pending')  # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship('Project', back_populates='quotes')
    recipient = relationship('User', back_populates='quotes')

class Message(Base):
    __tablename__ = 'message'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship('Project', back_populates='messages')
    sender = relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    receiver = relationship('User', foreign_keys=[receiver_id], back_populates='received_messages')

class ClosureFile(Base):
    __tablename__ = 'closure_file'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    uploader_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # pending, accepted, returned
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship('Project', back_populates='closure_files')
    uploader = relationship('User', back_populates='uploaded_files')

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
def verify_password(plain_password, hashed_password):
    """
    驗證密碼，支持多種哈希格式：
    - bcrypt (新格式)
    - pbkdf2:sha256 (werkzeug/Flask 格式)
    """
    # 首先嘗試使用 passlib 驗證（支持 bcrypt 和 pbkdf2_sha256）
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 如果 passlib 無法識別，嘗試使用 werkzeug 格式
        # werkzeug 的 check_password_hash 參數順序是 (hash, password)
        try:
            from werkzeug.security import check_password_hash
            return check_password_hash(hashed_password, plain_password)
        except Exception:
            return False

def get_password_hash(password):
    """生成密碼哈希，使用 bcrypt（新格式）"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user

def require_auth(current_user: Optional[User] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return current_user

def require_role(role: str):
    def role_checker(current_user: User = Depends(require_auth)):
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return current_user
    return role_checker

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    
    if db.query(User).filter(User.username == username).first():
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': 'Username already exists'}
        )
    
    if db.query(User).filter(User.email == email).first():
        return JSONResponse(
            status_code=400,
            content={'success': False, 'message': 'Email already exists'}
        )
    
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role=role
    )
    db.add(user)
    db.commit()
    
    return JSONResponse(content={'success': True, 'message': 'Registration successful'})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    username = data.get('username')
    password = data.get('password')
    
    user = db.query(User).filter(User.username == username).first()
    
    if user and verify_password(password, user.password_hash):
        access_token = create_access_token(data={"user_id": user.id})
        response = JSONResponse(content={
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        })
        response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=86400)
        return response
    
    return JSONResponse(
        status_code=401,
        content={'success': False, 'message': 'Invalid username or password'}
    )

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(require_auth)):
    if current_user.role == 'delegator':
        return templates.TemplateResponse("delegator_dashboard.html", {"request": request})
    else:
        return templates.TemplateResponse("recipient_dashboard.html", {"request": request})

# API Routes for Delegators
@app.get("/api/projects")
async def get_projects(current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.delegator_id == current_user.id).all()
    return [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'status': p.status,
        'delegate_id': p.delegate_id,
        'delegate_name': p.delegate.username if p.delegate else None,
        'created_at': p.created_at.isoformat(),
        'quote_count': len(p.quotes)
    } for p in projects]

@app.post("/api/projects")
async def create_project(request: Request, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    data = await request.json()
    project = Project(
        title=data.get('title'),
        description=data.get('description'),
        delegator_id=current_user.id,
        status='pending'
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return JSONResponse(content={'success': True, 'project_id': project.id})

@app.get("/api/projects/{project_id}")
async def get_project(project_id: int, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {
        'id': project.id,
        'title': project.title,
        'description': project.description,
        'status': project.status
    }

@app.put("/api/projects/{project_id}")
async def update_project(project_id: int, request: Request, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if project.status != 'pending':
        raise HTTPException(status_code=400, detail="Cannot modify project that is not pending")
    
    data = await request.json()
    project.title = data.get('title', project.title)
    project.description = data.get('description', project.description)
    db.commit()
    return JSONResponse(content={'success': True})

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    db.delete(project)
    db.commit()
    return JSONResponse(content={'success': True})

@app.get("/api/projects/{project_id}/quotes")
async def get_quotes(project_id: int, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    quotes = db.query(Quote).filter(Quote.project_id == project_id).all()
    return [{
        'id': q.id,
        'recipient_name': q.recipient.username,
        'amount': q.amount,
        'message': q.message,
        'status': q.status,
        'created_at': q.created_at.isoformat()
    } for q in quotes]

@app.post("/api/projects/{project_id}/select_delegate")
async def select_delegate(project_id: int, request: Request, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    quote_id = data.get('quote_id')
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if quote.project_id != project_id:
        raise HTTPException(status_code=400, detail="Invalid quote")
    
    project.delegate_id = quote.recipient_id
    project.status = 'active'
    quote.status = 'accepted'
    
    # Reject other quotes
    db.query(Quote).filter(and_(Quote.project_id == project_id, Quote.id != quote_id)).update({'status': 'rejected'}, synchronize_session=False)
    
    db.commit()
    return JSONResponse(content={'success': True})

@app.post("/api/projects/{project_id}/close")
async def close_project(project_id: int, request: Request, current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user.role == 'delegator' and project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    action = data.get('action')  # 'accept' or 'return'
    
    if action == 'accept':
        project.status = 'closed'
        db.query(ClosureFile).filter(and_(ClosureFile.project_id == project_id, ClosureFile.status == 'pending')).update({'status': 'accepted'}, synchronize_session=False)
    elif action == 'return':
        db.query(ClosureFile).filter(and_(ClosureFile.project_id == project_id, ClosureFile.status == 'pending')).update({'status': 'returned'}, synchronize_session=False)
    
    db.commit()
    return JSONResponse(content={'success': True})

# API Routes for Recipients
@app.get("/api/available_projects")
async def available_projects(current_user: User = Depends(require_role("recipient")), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.status == 'pending').all()
    user_quotes = {q.project_id for q in db.query(Quote).filter(Quote.recipient_id == current_user.id).all()}
    
    return [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'delegator_name': p.delegator.username,
        'created_at': p.created_at.isoformat(),
        'has_quoted': p.id in user_quotes,
        'quote_count': len(p.quotes)
    } for p in projects]

@app.post("/api/projects/{project_id}/quote")
async def submit_quote(project_id: int, request: Request, current_user: User = Depends(require_role("recipient")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != 'pending':
        raise HTTPException(status_code=400, detail="Project is not available for quoting")
    
    # Check if already quoted
    existing = db.query(Quote).filter(Quote.project_id == project_id, Quote.recipient_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted a quote for this project")
    
    data = await request.json()
    quote = Quote(
        project_id=project_id,
        recipient_id=current_user.id,
        amount=data.get('amount'),
        message=data.get('message', '')
    )
    db.add(quote)
    db.commit()
    return JSONResponse(content={'success': True})

@app.get("/api/my_projects")
async def my_projects(current_user: User = Depends(require_role("recipient")), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.delegate_id == current_user.id).all()
    return [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'status': p.status,
        'delegator_name': p.delegator.username,
        'created_at': p.created_at.isoformat()
    } for p in projects]

@app.post("/api/projects/{project_id}/upload_closure")
async def upload_closure_file(
    project_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("recipient")),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Secure filename
    timestamp = datetime.now().timestamp()
    original_filename = secure_filename(file.filename)
    safe_filename = f"{project_id}_{current_user.id}_{timestamp}_{original_filename}"
    filepath = os.path.join("uploads", safe_filename)
    
    # Save file
    with open(filepath, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    closure_file = ClosureFile(
        project_id=project_id,
        uploader_id=current_user.id,
        filename=safe_filename,
        original_filename=original_filename,
        status='pending'
    )
    db.add(closure_file)
    db.commit()
    db.refresh(closure_file)
    
    return JSONResponse(content={'success': True, 'file_id': closure_file.id})

# Communication Routes
@app.get("/api/projects/{project_id}/messages")
async def get_messages(project_id: int, current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user is part of the project
    if current_user.role == 'delegator':
        if project.delegator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        if project.delegate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    
    messages = db.query(Message).filter(Message.project_id == project_id).order_by(Message.created_at).all()
    return [{
        'id': m.id,
        'sender_name': m.sender.username,
        'sender_id': m.sender_id,
        'content': m.content,
        'created_at': m.created_at.isoformat()
    } for m in messages]

@app.post("/api/projects/{project_id}/messages")
async def create_message(project_id: int, request: Request, current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify user is part of the project and determine receiver
    if current_user.role == 'delegator':
        if project.delegator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        receiver_id = project.delegate_id
    else:
        if project.delegate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        receiver_id = project.delegator_id
    
    if not receiver_id:
        raise HTTPException(status_code=400, detail="No delegate assigned to project")
    
    data = await request.json()
    message = Message(
        project_id=project_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=data.get('content')
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return JSONResponse(content={'success': True, 'message_id': message.id})

# History Routes
@app.get("/api/history")
async def project_history(current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    if current_user.role == 'delegator':
        projects = db.query(Project).filter(
            Project.delegator_id == current_user.id,
            Project.status.in_(['completed', 'closed'])
        ).all()
    else:
        projects = db.query(Project).filter(
            Project.delegate_id == current_user.id,
            Project.status.in_(['completed', 'closed'])
        ).all()
    
    return [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'status': p.status,
        'delegate_name': p.delegate.username if p.delegate else None,
        'delegator_name': p.delegator.username,
        'created_at': p.created_at.isoformat(),
        'completed_at': p.updated_at.isoformat()
    } for p in projects]

if __name__ == '__main__':
    import uvicorn
    import socket
    import sys
    
    def find_free_port(start_port=5000, max_attempts=10):
        """尋找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return None
    
    # 嘗試使用端口 5000，如果被佔用則尋找其他可用端口
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}. Using default port 5000.")
    
    # 檢查端口是否可用
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        test_socket.bind(('127.0.0.1', port))
        test_socket.close()
    except OSError:
        print(f"Port {port} is already in use. Searching for available port...")
        free_port = find_free_port(5000)
        if free_port:
            port = free_port
            print(f"Using port {port} instead.")
        else:
            print("Could not find an available port. Please free up a port and try again.")
            sys.exit(1)
    
    print("=" * 50)
    print("Starting FastAPI server...")
    print("=" * 50)
    print(f"✓ Port {port} is available")
    print(f"✓ Server will start on: http://127.0.0.1:{port}")
    print(f"✓ Access from browser: http://localhost:{port}")
    print("-" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    print()
    
    try:
        # 使用 127.0.0.1 而不是 0.0.0.0 以避免權限問題
        # 如果需要從網絡訪問，可以改為 "0.0.0.0"，但可能需要管理員權限
        # 使用導入字符串 "app:app" 以支持 reload 功能
        uvicorn.run(
            "app:app", 
            host="127.0.0.1", 
            port=port, 
            reload=True,
            log_level="info"
        )
    except PermissionError:
        print("\n" + "=" * 50)
        print("ERROR: Permission denied!")
        print("=" * 50)
        print("The server requires administrator privileges to bind to this port.")
        print("\nSolutions:")
        print("1. Run as administrator (right-click and 'Run as administrator')")
        print("2. Use a different port (e.g., python app.py 8000)")
        print("3. Change host to 127.0.0.1 (already set)")
        print("=" * 50)
        sys.exit(1)
    except OSError as e:
        print("\n" + "=" * 50)
        print(f"ERROR: Could not start server on port {port}")
        print("=" * 50)
        print(f"Error details: {e}")
        print("\nTrying alternative port 8000...")
        print("=" * 50)
        try:
            uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
        except Exception as e2:
            print(f"\nFailed to start on port 8000: {e2}")
            print("\nPlease check:")
            print("1. No other application is using these ports")
            print("2. Firewall is not blocking the connection")
            print("3. You have necessary permissions")
            sys.exit(1)