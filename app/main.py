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

DATABASE_URL = os.environ.get("DATABASE_URL")
# IMPORTANT: This key must match the one in your HTML exactly
API_KEY = os.environ.get("API_KEY", "some-long-random-string")

if not DATABASE_URL:
    # Fallback for local testing
    DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================
# 2. FastAPI Initialization (Fixes NameError)
# =====================================================

app = FastAPI(title="Gen2 Repair API", version="3.1.0")

# HARDENED CORS: Required for Cloudflare -> Render communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# =====================================================
# 3. Database Models (SQLAlchemy)
# =====================================================

class Repair(Base):
    __tablename__ = "repairs"
    repair_uid = Column(String, primary_key=True, index=True)
    hull_id = Column(String, nullable=False)
    date_opened = Column(Date, nullable=False)
    location = Column(String)
    technicians = Column(String)
    issue_desc = Column(Text)
    service_type = Column(String)

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
    notes = Column(Text)

# Create tables in DB
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
    Validates API Key but allows OPTIONS (CORS pre-flight) to pass.
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
    subsystem: str
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
    """Confirms API is alive and prevents 404 logs."""
    return {"status": "online", "message": "Gen2 Repair API v3.1"}

@app.get("/health")
def health_check():
    """Endpoint for frontend connectivity testing."""
    return {"status": "healthy"}

@app.get("/repairs")
def list_repairs(db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Fetch all repairs for the frontend history log."""
    return db.query(Repair).all()

@app.post("/repairs")
def create_repair(repair: RepairCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Creates the master repair record."""
    new_uid = str(uuid.uuid4())
    db_repair = Repair(repair_uid=new_uid, **repair.model_dump())
    db.add(db_repair)
    db.commit()
    db.refresh(db_repair)
    return db_repair

@app.post("/repairs/{repair_uid}/component-changes")
def add_component_change(repair_uid: str, change: ComponentChangeCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Adds a hardware swap to a specific repair."""
    db_change = ComponentChange(id=str(uuid.uuid4()), repair_uid=repair_uid, **change.model_dump())
    db.add(db_change)
    db.commit()
    return {"status": "success"}

@app.post("/repairs/{repair_uid}/config-changes")
def add_config_change(repair_uid: str, change: ConfigChangeCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Adds a config parameter change to a specific repair."""
    db_change = ConfigChange(id=str(uuid.uuid4()), repair_uid=repair_uid, **change.model_dump())
    db.add(db_change)
    db.commit()
    return {"status": "success"}
