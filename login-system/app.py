from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
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
    proposal_files = relationship('ProposalFile', foreign_keys='ProposalFile.uploader_id')

class Project(Base):
    __tablename__ = 'project'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='pending')  # pending, active, completed, closed
    delegator_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    delegate_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    deadline = Column(DateTime, nullable=True)  # 提案截止期限
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    delegator = relationship('User', foreign_keys=[delegator_id], back_populates='delegated_projects')
    delegate = relationship('User', foreign_keys=[delegate_id], back_populates='received_projects')
    quotes = relationship('Quote', back_populates='project')
    messages = relationship('Message', back_populates='project')
    closure_files = relationship('ClosureFile', back_populates='project')
    proposal_files = relationship('ProposalFile', back_populates='project')

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
    proposal_file = relationship('ProposalFile', back_populates='quote', uselist=False)

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

class ProposalFile(Base):
    __tablename__ = 'proposal_file'
    
    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey('quote.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    uploader_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    quote = relationship('Quote', back_populates='proposal_file')
    project = relationship('Project', back_populates='proposal_files')
    uploader = relationship('User', foreign_keys=[uploader_id])

class ClosureFile(Base):
    __tablename__ = 'closure_file'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    uploader_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    version = Column(Integer, default=1)  # 版本號
    status = Column(String(20), default='pending')  # pending, accepted, returned
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship('Project', back_populates='closure_files')
    uploader = relationship('User', back_populates='uploaded_files')

# Create tables
Base.metadata.create_all(bind=engine)

# 數據庫遷移：添加 deadline 字段（如果不存在）
def migrate_database():
    """檢查並添加缺失的數據庫字段"""
    from sqlalchemy import inspect, text
    
    inspector = inspect(engine)
    
    # 檢查 project 表是否存在 deadline 字段
    if 'project' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('project')]
        if 'deadline' not in columns:
            print("正在添加 deadline 字段到 project 表...")
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE project ADD COLUMN deadline DATETIME"))
                print("✓ deadline 字段已添加")
            except Exception as e:
                print(f"添加 deadline 字段時出錯: {e}")
    
    # 檢查 closure_file 表是否存在 version 字段
    if 'closure_file' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('closure_file')]
        if 'version' not in columns:
            print("正在添加 version 字段到 closure_file 表...")
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE closure_file ADD COLUMN version INTEGER DEFAULT 1"))
                print("✓ version 字段已添加")
            except Exception as e:
                print(f"添加 version 字段時出錯: {e}")
    
    # 檢查是否存在 proposal_file 表，如果不存在則創建
    if 'proposal_file' not in inspector.get_table_names():
        print("正在創建 proposal_file 表...")
        try:
            ProposalFile.__table__.create(bind=engine, checkfirst=True)
            print("✓ proposal_file 表已創建")
        except Exception as e:
            print(f"創建 proposal_file 表時出錯: {e}")

# 執行遷移
try:
    migrate_database()
except Exception as e:
    print(f"數據庫遷移警告: {e}")
    print("如果這是第一次運行，這是正常的。")

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
        'deadline': p.deadline.isoformat() if p.deadline else None,
        'created_at': p.created_at.isoformat(),
        'quote_count': len(p.quotes)
    } for p in projects]

@app.post("/api/projects")
async def create_project(request: Request, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    data = await request.json()
    
    # 解析截止日期
    deadline = None
    if data.get('deadline'):
        try:
            deadline_str = data.get('deadline')
            # 處理不同的日期格式
            if deadline_str.endswith('Z'):
                deadline_str = deadline_str.replace('Z', '+00:00')
            elif '+' not in deadline_str and '-' not in deadline_str[-6:] and 'T' in deadline_str:
                # 如果沒有時區信息，假設是UTC
                deadline_str = deadline_str + '+00:00'
            
            # 解析日期
            if '+' in deadline_str or deadline_str.endswith('Z'):
                # 帶時區的格式
                deadline = datetime.fromisoformat(deadline_str)
                # 轉換為UTC時間（naive datetime）
                if deadline.tzinfo:
                    deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                # 不帶時區的格式，直接解析
                deadline = datetime.fromisoformat(deadline_str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid deadline format: {str(e)}")
    
    project = Project(
        title=data.get('title'),
        description=data.get('description'),
        delegator_id=current_user.id,
        status='pending',
        deadline=deadline
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
        'status': project.status,
        'deadline': project.deadline.isoformat() if project.deadline else None
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
    
    # 更新截止日期
    if 'deadline' in data:
        if data.get('deadline'):
            try:
                deadline_str = data.get('deadline')
                # 處理不同的日期格式
                if deadline_str.endswith('Z'):
                    deadline_str = deadline_str.replace('Z', '+00:00')
                elif '+' not in deadline_str and '-' not in deadline_str[-6:] and 'T' in deadline_str:
                    # 如果沒有時區信息，假設是UTC
                    deadline_str = deadline_str + '+00:00'
                
                # 解析日期
                if '+' in deadline_str or deadline_str.endswith('Z'):
                    # 帶時區的格式
                    deadline = datetime.fromisoformat(deadline_str)
                    # 轉換為UTC時間（naive datetime）
                    if deadline.tzinfo:
                        deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    # 不帶時區的格式，直接解析
                    deadline = datetime.fromisoformat(deadline_str)
                project.deadline = deadline
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid deadline format: {str(e)}")
        else:
            project.deadline = None
    
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
        'created_at': q.created_at.isoformat(),
        'proposal_file': {
            'id': q.proposal_file.id,
            'original_filename': q.proposal_file.original_filename,
            'filename': q.proposal_file.filename,
            'created_at': q.proposal_file.created_at.isoformat()
        } if q.proposal_file else None
    } for q in quotes]

@app.post("/api/projects/{project_id}/select_delegate")
async def select_delegate(project_id: int, request: Request, current_user: User = Depends(require_role("delegator")), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 檢查是否已過截止日期
    if project.deadline and datetime.utcnow() < project.deadline:
        raise HTTPException(status_code=400, detail="Cannot select delegate before deadline")
    
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

@app.get("/api/projects/{project_id}/closure_files")
async def get_closure_files(project_id: int, current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 驗證用戶權限
    # 委託方可以查看自己項目的結案文件
    if current_user.role == 'delegator':
        if project.delegator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    # 受託方可以查看自己被委託項目的結案文件
    elif current_user.role == 'recipient':
        if project.delegate_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 查詢文件，處理可能為NULL的version字段
    # 使用COALESCE將NULL值轉換為0，確保排序正常
    from sqlalchemy import func
    files = db.query(ClosureFile).filter(ClosureFile.project_id == project_id).order_by(
        desc(func.coalesce(ClosureFile.version, 0)),
        desc(ClosureFile.created_at)
    ).all()
    return [{
        'id': f.id,
        'filename': f.filename,
        'original_filename': f.original_filename,
        'version': f.version if f.version is not None else 1,  # 處理舊記錄可能沒有version的情況
        'status': f.status,
        'uploader_name': f.uploader.username if f.uploader else '未知',
        'created_at': f.created_at.isoformat() if f.created_at else datetime.utcnow().isoformat()
    } for f in files]

@app.get("/api/files/{file_id}/download")
async def download_file(file_id: int, file_type: str = "closure", current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """下載文件（支持提案文件和結案文件）"""
    if file_type == "proposal":
        file_record = db.query(ProposalFile).filter(ProposalFile.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 驗證權限：提案者本人或項目委託方可以下載
        quote = db.query(Quote).filter(Quote.id == file_record.quote_id).first()
        project = db.query(Project).filter(Project.id == file_record.project_id).first()
        
        if current_user.id != file_record.uploader_id and (current_user.role != 'delegator' or project.delegator_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden")
    else:  # closure
        file_record = db.query(ClosureFile).filter(ClosureFile.id == file_id).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 驗證權限：上傳者本人或項目委託方可以下載
        project = db.query(Project).filter(Project.id == file_record.project_id).first()
        if current_user.id != file_record.uploader_id and (current_user.role != 'delegator' or project.delegator_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden")
    
    filepath = os.path.join("uploads", file_record.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        path=filepath,
        filename=file_record.original_filename,
        media_type='application/pdf'
    )

@app.post("/api/projects/{project_id}/close")
async def close_project(project_id: int, request: Request, current_user: User = Depends(require_auth), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user.role == 'delegator' and project.delegator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    data = await request.json()
    action = data.get('action')  # 'accept' or 'return'
    file_id = data.get('file_id')  # 可選：指定接受的文件ID
    
    if action == 'accept':
        project.status = 'closed'
        if file_id:
            # 接受指定版本的文件
            file_record = db.query(ClosureFile).filter(ClosureFile.id == file_id).first()
            if file_record and file_record.project_id == project_id:
                file_record.status = 'accepted'
        else:
            # 接受所有pending的文件
            db.query(ClosureFile).filter(and_(ClosureFile.project_id == project_id, ClosureFile.status == 'pending')).update({'status': 'accepted'}, synchronize_session=False)
    elif action == 'return':
        if file_id:
            # 退回指定版本的文件
            file_record = db.query(ClosureFile).filter(ClosureFile.id == file_id).first()
            if file_record and file_record.project_id == project_id:
                file_record.status = 'returned'
        else:
            # 退回所有pending的文件
            db.query(ClosureFile).filter(and_(ClosureFile.project_id == project_id, ClosureFile.status == 'pending')).update({'status': 'returned'}, synchronize_session=False)
    
    db.commit()
    return JSONResponse(content={'success': True})

# API Routes for Recipients
@app.get("/api/available_projects")
async def available_projects(current_user: User = Depends(require_role("recipient")), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    # 只顯示pending狀態且未過截止日期的項目
    projects = db.query(Project).filter(
        Project.status == 'pending'
    ).filter(
        or_(Project.deadline.is_(None), Project.deadline > now)
    ).all()
    user_quotes = {q.project_id for q in db.query(Quote).filter(Quote.recipient_id == current_user.id).all()}
    
    return [{
        'id': p.id,
        'title': p.title,
        'description': p.description,
        'delegator_name': p.delegator.username,
        'deadline': p.deadline.isoformat() if p.deadline else None,
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
    
    # 檢查是否已過截止日期
    if project.deadline and datetime.utcnow() >= project.deadline:
        raise HTTPException(status_code=400, detail="Project deadline has passed")
    
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
    db.refresh(quote)
    return JSONResponse(content={'success': True, 'quote_id': quote.id})

@app.post("/api/quotes/{quote_id}/upload_proposal")
async def upload_proposal_file(
    quote_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("recipient")),
    db: Session = Depends(get_db)
):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    project = db.query(Project).filter(Project.id == quote.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 檢查是否已過截止日期
    if project.deadline and datetime.utcnow() >= project.deadline:
        raise HTTPException(status_code=400, detail="Project deadline has passed")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # 檢查文件格式（只允許PDF）
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # 檢查文件內容類型
    content_type = file.content_type
    if content_type and content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # 生成唯一檔名（避免覆蓋）
    timestamp = datetime.now().timestamp()
    original_filename = secure_filename(file.filename)
    safe_filename = f"proposal_{quote_id}_{current_user.id}_{timestamp}_{original_filename}"
    filepath = os.path.join("uploads", safe_filename)
    
    # 保存文件
    with open(filepath, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # 檢查是否已有提案文件，如果有則刪除舊的（但保留文件）
    existing_file = db.query(ProposalFile).filter(ProposalFile.quote_id == quote_id).first()
    if existing_file:
        # 不刪除文件，只更新記錄
        existing_file.filename = safe_filename
        existing_file.original_filename = original_filename
        existing_file.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_file)
        return JSONResponse(content={'success': True, 'file_id': existing_file.id})
    else:
        proposal_file = ProposalFile(
            quote_id=quote_id,
            project_id=quote.project_id,
            uploader_id=current_user.id,
            filename=safe_filename,
            original_filename=original_filename
        )
        db.add(proposal_file)
        db.commit()
        db.refresh(proposal_file)
        return JSONResponse(content={'success': True, 'file_id': proposal_file.id})

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
    
    # 計算版本號（獲取該項目當前最高版本號+1）
    max_version = db.query(ClosureFile).filter(
        ClosureFile.project_id == project_id,
        ClosureFile.uploader_id == current_user.id
    ).order_by(ClosureFile.version.desc()).first()
    
    version = (max_version.version + 1) if max_version else 1
    
    # 生成唯一檔名（包含版本號，避免覆蓋）
    timestamp = datetime.now().timestamp()
    original_filename = secure_filename(file.filename)
    safe_filename = f"closure_{project_id}_{current_user.id}_v{version}_{timestamp}_{original_filename}"
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
        version=version,
        status='pending'
    )
    db.add(closure_file)
    db.commit()
    db.refresh(closure_file)
    
    return JSONResponse(content={'success': True, 'file_id': closure_file.id, 'version': version})

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