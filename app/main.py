import os
import uuid
from datetime import date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Header
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
# Make sure this matches the key you put in your HTML form
API_KEY = os.environ.get("API_KEY", "some-long-random-string")

if not DATABASE_URL:
    # Fallback to local sqlite if DATABASE_URL is missing
    DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================
# 2. FastAPI Initialization (MUST COME BEFORE MIDDLEWARE)
# =====================================================

app = FastAPI(title="Gen2 Repair API", version="3.0.0")

# CORS setup allows your Cloudflare/frontend domain to talk to Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    service_type = Column(String)
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
    performed_by = Column(String)

class ConfigChange(Base):
    __tablename__ = "config_changes"
    id = Column(String, primary_key=True, index=True)
    repair_uid = Column(String, ForeignKey("repairs.repair_uid"))
    system = Column(String)
    parameter = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    notes = Column(Text)

# Create tables in the DB
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

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

# =====================================================
# 5. Pydantic Schemas (Input Validation)
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
    notes: Optional[str] = None

# =====================================================
# 6. API Routes
# =====================================================

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/repairs")
def list_repairs(
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Fetches all repairs for the frontend log."""
    return db.query(Repair).all()

@app.post("/repairs")
def create_repair(
    repair: RepairCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Creates the master record and returns the UID."""
    new_uid = str(uuid.uuid4())
    db_repair = Repair(repair_uid=new_uid, **repair.model_dump())
    db.add(db_repair)
    db.commit()
    db.refresh(db_repair)
    return db_repair

@app.post("/repairs/{repair_uid}/component-changes")
def add_component_change(
    repair_uid: str, 
    change: ComponentChangeCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    db_change = ComponentChange(
        id=str(uuid.uuid4()), 
        repair_uid=repair_uid, 
        **change.model_dump()
    )
    db.add(db_change)
    db.commit()
    return {"status": "success"}

@app.post("/repairs/{repair_uid}/config-changes")
def add_config_change(
    repair_uid: str, 
    change: ConfigChangeCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    db_change = ConfigChange(
        id=str(uuid.uuid4()), 
        repair_uid=repair_uid, 
        **change.model_dump()
    )
    db.add(db_change)
    db.commit()
    return {"status": "success"}
