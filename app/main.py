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
API_KEY = os.environ.get("API_KEY", "some-long-random-string")

if not DATABASE_URL:
    # Fallback to sqlite for local testing if DATABASE_URL is missing
    DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================
# 2. FastAPI Initialization & CORS
# =====================================================

app = FastAPI(title="Gen2 Repair API", version="3.0.0")

# CORS must be defined immediately after 'app' is created
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your Cloudflare Worker domain
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
    old_fw = Column(String)
    new_fw = Column(String)
    reason = Column(Text)
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

# Create tables if they don't exist
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
# 5. Pydantic Schemas (Validation)
# =====================================================

class RepairCreate(BaseModel):
    hull_id: str
    date_opened: date
    location: Optional[str] = None
    technicians: Optional[str] = None
    service_type: Optional[str] = None
    issue_desc: Optional[str] = None

class ComponentChangeCreate(BaseModel):
    subsystem: Optional[str] = None
    component: Optional[str] = None
    old_serial: Optional[str] = None
    new_serial: Optional[str] = None
    old_fw: Optional[str] = None
    new_fw: Optional[str] = None
    reason: Optional[str] = None
    change_date: Optional[date] = None
    performed_by: Optional[str] = None

class ConfigChangeCreate(BaseModel):
    system: Optional[str] = None
    parameter: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    notes: Optional[str] = None

# =====================================================
# 6. API Routes
# =====================================================

@app.get("/")
def root():
    return {"status": "online", "message": "Gen2 Repair API v3"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Repair Routes ---

@app.get("/repairs")
def list_repairs(
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Fetch all repairs from the database."""
    return db.query(Repair).all()

@app.post("/repairs")
def create_repair(
    repair: RepairCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Create a new master repair record."""
    new_uid = str(uuid.uuid4())
    db_repair = Repair(
        repair_uid=new_uid,
        **repair.model_dump()
    )
    db.add(db_repair)
    db.commit()
    db.refresh(db_repair)
    return db_repair

# --- Sub-item Routes ---

@app.post("/repairs/{repair_uid}/component-changes")
def add_component_change(
    repair_uid: str, 
    change: ComponentChangeCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Add a hardware swap record to a specific repair."""
    db_change = ComponentChange(
        id=str(uuid.uuid4()),
        repair_uid=repair_uid,
        **change.model_dump()
    )
    db.add(db_change)
    db.commit()
    return {"status": "success", "id": db_change.id}

@app.post("/repairs/{repair_uid}/config-changes")
def add_config_change(
    repair_uid: str, 
    change: ConfigChangeCreate, 
    db: Session = Depends(get_db), 
    _: None = Depends(verify_api_key)
):
    """Add a parameter/config change record to a specific repair."""
    db_change = ConfigChange(
        id=str(uuid.uuid4()),
        repair_uid=repair_uid,
        **change.model_dump()
    )
    db.add(db_change)
    db.commit()
    return {"status": "success", "id": db_change.id}
