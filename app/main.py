import os
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import make_engine, make_session_local
from . import crud
from .models import Repair
from .schemas import (
    RepairCreate, RepairUpdate, RepairOut,
    ComponentChangeCreate, ConfigChangeCreate,
    ChecklistItemOut, ChecklistUpdate
)

DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

engine = make_engine(DATABASE_URL)
SessionLocal = make_session_local(engine)

app = FastAPI(title="Gen2 Repair API", version="0.1.0")

# CORS: set your deployed web app origin(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def require_api_key(x_api_key: str | None = Header(default=None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def repair_to_out(rep: Repair) -> RepairOut:
    hull_id = rep.vessel.hull_id if rep.vessel else ""

    snapshot = {
        "ilmor_sn": rep.snapshot_ilmor_sn,
        "ilmor_fw": rep.snapshot_ilmor_fw,
        "icu_sn": rep.snapshot_icu_sn,
        "orca_sn": rep.snapshot_orca_sn,
        "battery_sns": rep.snapshot_battery_sns,
        "camera": rep.snapshot_camera,
        "radar": rep.snapshot_radar,
        "compass": rep.snapshot_compass,
        "two_battery": rep.snapshot_two_battery,
    }

    checklist = {}
    for rc in rep.checklist:
        if rc.item and rc.item.code:
            checklist[rc.item.code] = bool(rc.checked)

    return RepairOut(
        repair_uid=rep.repair_uid,
        hull_id=hull_id,
        date_opened=rep.date_opened,
        location=rep.location,
        ticket=rep.ticket,
        technicians=rep.technicians,
        program=rep.program,
        service_type=rep.service_type,
        root_cause_cat=rep.root_cause_cat,
        issue_desc=rep.issue_desc,
        root_cause_details=rep.root_cause_details,
        wiring_notes=rep.wiring_notes,
        structural_notes=rep.structural_notes,
        verification_notes=rep.verification_notes,
        final_status=rep.final_status,
        limitations=rep.limitations,
        snapshot=snapshot,
        component_changes=[{
            **{
                "subsystem": c.subsystem,
                "component": c.component,
                "old_serial": c.old_serial,
                "new_serial": c.new_serial,
                "old_fw": c.old_fw,
                "new_fw": c.new_fw,
                "reason": c.reason,
                "performed_by": c.performed_by,
                "change_date": c.change_date,
            },
            "id": int(c.id),
            "created_at": c.created_at,
        } for c in rep.component_changes],
        config_changes=[{
            **{
                "system": c.system,
                "parameter": c.parameter,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "reason": c.reason,
            },
            "id": int(c.id),
            "created_at": c.created_at,
        } for c in rep.config_changes],
        checklist=checklist
    )

@app.post("/repairs", dependencies=[Depends(require_api_key)], response_model=RepairOut)
def create_repair(payload: RepairCreate, db: Session = Depends(get_db)):
    rep = crud.create_repair(db, payload)
    db.commit()
    db.refresh(rep)
    # load relationships
    rep = crud.get_repair_by_uid(db, rep.repair_uid)
    return repair_to_out(rep)

@app.get("/repairs", dependencies=[Depends(require_api_key)], response_model=list[RepairOut])
def list_repairs(
    hull_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    reps = crud.list_repairs(db, hull_id, date_from, date_to, limit)
    # ensure vessel relationship present
    out = []
    for r in reps:
        r = crud.get_repair_by_uid(db, r.repair_uid)
        out.append(repair_to_out(r))
    return out

@app.get("/repairs/{repair_uid}", dependencies=[Depends(require_api_key)], response_model=RepairOut)
def get_repair(repair_uid: str, db: Session = Depends(get_db)):
    rep = crud.get_repair_by_uid(db, repair_uid)
    if not rep:
        raise HTTPException(404, "Not found")
    # eager-load relationships via access
    _ = rep.vessel, rep.component_changes, rep.config_changes, rep.checklist
    return repair_to_out(rep)

@app.patch("/repairs/{repair_uid}", dependencies=[Depends(require_api_key)], response_model=RepairOut)
def patch_repair(repair_uid: str, payload: RepairUpdate, db: Session = Depends(get_db)):
    rep = crud.get_repair_by_uid(db, repair_uid)
    if not rep:
        raise HTTPException(404, "Not found")
    crud.update_repair(db, rep, payload)
    db.commit()
    rep = crud.get_repair_by_uid(db, repair_uid)
    return repair_to_out(rep)

@app.post("/repairs/{repair_uid}/component-changes", dependencies=[Depends(require_api_key)])
def add_component_change(repair_uid: str, payload: ComponentChangeCreate, db: Session = Depends(get_db)):
    rep = crud.get_repair_by_uid(db, repair_uid)
    if not rep:
        raise HTTPException(404, "Not found")
    crud.add_component_change(db, rep, payload)
    db.commit()
    return {"ok": True}

@app.delete("/component-changes/{change_id}", dependencies=[Depends(require_api_key)])
def remove_component_change(change_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_component_change(db, change_id)
    if not ok:
        raise HTTPException(404, "Not found")
    db.commit()
    return {"ok": True}

@app.post("/repairs/{repair_uid}/config-changes", dependencies=[Depends(require_api_key)])
def add_config_change(repair_uid: str, payload: ConfigChangeCreate, db: Session = Depends(get_db)):
    rep = crud.get_repair_by_uid(db, repair_uid)
    if not rep:
        raise HTTPException(404, "Not found")
    crud.add_config_change(db, rep, payload)
    db.commit()
    return {"ok": True}

@app.delete("/config-changes/{change_id}", dependencies=[Depends(require_api_key)])
def remove_config_change(change_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_config_change(db, change_id)
    if not ok:
        raise HTTPException(404, "Not found")
    db.commit()
    return {"ok": True}

@app.get("/checklist-items", dependencies=[Depends(require_api_key)], response_model=list[ChecklistItemOut])
def checklist_items(db: Session = Depends(get_db)):
    items = crud.get_checklist_items(db)
    return [ChecklistItemOut(code=i.code, label=i.label, sort_order=i.sort_order, active=i.active) for i in items]

@app.put("/repairs/{repair_uid}/checklist", dependencies=[Depends(require_api_key)])
def update_checklist(repair_uid: str, payload: ChecklistUpdate, db: Session = Depends(get_db)):
    rep = crud.get_repair_by_uid(db, repair_uid)
    if not rep:
        raise HTTPException(404, "Not found")
    crud.upsert_repair_checklist(db, rep, payload.states)
    db.commit()
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}
