import os
import uuid
from datetime import date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Date,
    Text,
    ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# =====================================================
# 1. Configuration & Database Setup
# =====================================================

# DATABASE_URL should be set in Render Env Vars. 
# Fallback to local sqlite for safety.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")

# This must match the key you type into the HTML portal exactly
API_KEY = os.environ.get("API_KEY", "some-long-random-string")

engine = create_engine(
    DATABASE_URL, 
    # SQLite specific fix; remove connect_args if using PostgreSQL
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================
# 2. FastAPI Initialization
# =====================================================

app = FastAPI(title="Gen2 Repair API", version="3.2.0")

# PERMISSIVE CORS: This is critical to fix "Failed to fetch"
# It allows your Cloudflare domain to send custom headers like X-API-Key
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization", "Accept"],
)

# =====================================================
# 3. Database Models
# =====================================================

class Repair(Base):
    __tablename__ = "repairs"
    repair_uid = Column(String, primary_key=True, index=True)
    hull_id = Column(String, nullable=False)
    date_opened = Column(Date, nullable=False)
    location = Column(String)
    technicians = Column(String)
    issue_desc = Column(Text)

class ComponentChange(Base):
    __tablename__ = "component_changes"
    id = Column(String, primary_key=True, index=True)
    repair_uid = Column(String, ForeignKey("repairs.repair_uid"))
    subsystem = Column(String)
    component = Column(String)
    old_serial = Column(String)
    new_serial = Column(String)
    change_date = Column(Date)

class ConfigChange(Base):
    __tablename__ = "config_changes"
    id = Column(String, primary_key=True, index=True)
    repair_uid = Column(String, ForeignKey("repairs.repair_uid"))
    parameter = Column(String)
    old_value = Column(String)
    new_value = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# =====================================================
# 4. Dependencies
# =====================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    """
    SECURITY FIX: Browsers send an 'OPTIONS' request before a 'POST'.
    We must allow OPTIONS requests to pass without an API key check,
    otherwise the CORS handshake will fail.
    """
    if request.method == "OPTIONS":
        return
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# =====================================================
# 5. Pydantic Schemas
# =====================================================

class RepairCreate(BaseModel):
    hull_id: str
    date_opened: date
    location: Optional[str] = None
    technicians: Optional[str] = None
    issue_desc: Optional[str] = None

class ComponentChangeCreate(BaseModel):
    subsystem: Optional[str] = None
    component: str
    old_serial: Optional[str] = None
    new_serial: Optional[str] = None
    change_date: Optional[date] = None

class ConfigChangeCreate(BaseModel):
    parameter: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

# =====================================================
# 6. API Routes
# =====================================================

@app.get("/")
def read_root():
    return {"status": "online", "message": "Gen2 Repair API v3.2 is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/repairs")
def list_repairs(db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    return db.query(Repair).all()

@app.post("/repairs")
def create_repair(repair: RepairCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    new_uid = str(uuid.uuid4())
    db_repair = Repair(repair_uid=new_uid, **repair.model_dump())
    db.add(db_repair)
    db.commit()
    db.refresh(db_repair)
    return db_repair

@app.post("/repairs/{repair_uid}/component-changes")
def add_component_change(repair_uid: str, change: ComponentChangeCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    db_change = ComponentChange(id=str(uuid.uuid4()), repair_uid=repair_uid, **change.model_dump())
    db.add(db_change)
    db.commit()
    return {"status": "success"}

@app.post("/repairs/{repair_uid}/config-changes")
def add_config_change(repair_uid: str, change: ConfigChangeCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    db_change = ConfigChange(id=str(uuid.uuid4()), repair_uid=repair_uid, **change.model_dump())
    db.add(db_change)
    db.commit()
    return {"status": "success"}
