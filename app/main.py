import os
import uuid
from datetime import date
from typing import Optional

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
# Configuration
# =====================================================

DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

# =====================================================
# CORS (IMPORTANT FOR WORKERS.DEV FRONTEND)
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://small-block-8bd7.william-javanainen.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],  # must allow X-API-Key
)

# =====================================================
# Database Models
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


Base.metadata.create_all(bind=engine)

# =====================================================
# Dependency
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
# Schemas
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
# Routes
# =====================================================

@app.get("/")
def root():
    return {"ok": True, "service": "gen2-repair-api-3"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/repairs")
def create_repair(
    repair: RepairCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repair_uid = str(uuid.uuid4())

    db_repair = Repair(
        repair_uid=repair_uid,
        hull_id=repair.hull_id,
        date_opened=repair.date_opened,
        location=repair.location,
        technicians=repair.technicians,
        service_type=repair.service_type,
        issue_desc=repair.issue_desc,
    )

    db.add(db_repair)
    db.commit()

    return {"repair_uid": repair_uid}


@app.post("/repairs/{repair_uid}/component-changes")
def add_component_change(
    repair_uid: str,
    change: ComponentChangeCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    db_change = ComponentChange(
        id=str(uuid.uuid4()),
        repair_uid=repair_uid,
        subsystem=change.subsystem,
        component=change.component,
        old_serial=change.old_serial,
        new_serial=change.new_serial,
        old_fw=change.old_fw,
        new_fw=change.new_fw,
        reason=change.reason,
        change_date=change.change_date,
        performed_by=change.performed_by,
    )

    db.add(db_change)
    db.commit()

    return {"status": "component change added"}


@app.post("/repairs/{repair_uid}/config-changes")
def add_config_change(
    repair_uid: str,
    change: ConfigChangeCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    db_change = ConfigChange(
        id=str(uuid.uuid4()),
        repair_uid=repair_uid,
        system=change.system,
        parameter=change.parameter,
        old_value=change.old_value,
        new_value=change.new_value,
        notes=change.notes,
    )

    db.add(db_change)
    db.commit()

    return {"status": "config change added"}
